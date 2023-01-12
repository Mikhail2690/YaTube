import shutil
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from http import HTTPStatus

from ..models import Post, Group, Comment
from ..forms import PostForm

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, f'/profile/{self.user.username}/')
        self.assertEqual(Post.objects.count(), 1)
        first_post = Post.objects.first()
        fields = {
            first_post.text: form_data['text'],
            first_post.group: self.group,
            first_post.author: self.user,
            first_post.image: f'posts/{uploaded}',
        }
        for value, excepted_value in fields.items():
            with self.subTest(value=value):
                self.assertEqual(value, excepted_value)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group,
        )
        new_group = Group.objects.create(
            title='Тестовая группа2',
            slug='test-group',
            description='Описание',
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Какой то новый текст',
            'group': new_group,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        first_post = Post.objects.first()
        fields = {
            first_post.text: form_data['text'],
            first_post.group: form_data['group'],
        }
        for value, excepted_value in fields.items():
            with self.subTest(value=value):
                self.assertNotEqual(value, excepted_value)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unauth_user_cant_publish_post(self):
        """Проверка редиректа неавторизованного пользователя"""
        guest_client = Client()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group,
        }
        response = guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')


class FormLabelsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.form = PostForm()

    def test_text_group_label(self):
        """Проверка полей label формы PostForm"""
        fields = {
            FormLabelsTests.form.fields['text'].label: 'Текст поста',
            FormLabelsTests.form.fields['group'].label: 'Группа',
        }
        for field, expected_object_name in fields.items():
            with self.subTest(field=field):
                self.assertEqual(field, expected_object_name)

    def test_text_group_help_text(self):
        """Проверка полей help_text формы PostForm"""
        fields = {
            FormLabelsTests.form.fields['text'].help_text:
            'Текст нового поста',
            FormLabelsTests.form.fields['group'].help_text:
            'Группа, к которой будет относиться пост',
        }
        for field, expected_object_name in fields.items():
            with self.subTest(field=field):
                self.assertEqual(field, expected_object_name)


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_form_create_comment(self):
        """Валидная форма создает запись в Comment."""
        form_data = {'text': 'Тестовый комментарий'}
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(response, f'/posts/{self.post.pk}/')
        self.assertEqual(Comment.objects.count(), 1)
        first_comment = Comment.objects.first()
        self.assertEqual(first_comment.text, form_data['text'])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_guest_client_cannot_comment(self):
        """Комментировать посты может только авторизованный пользователь."""
        guest_client = Client()
        count_comments = Comment.objects.count()
        form_data = {'text': 'Тестовый комментарий'}
        response = guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True,
        )
        self.assertEqual(count_comments, Comment.objects.count())
        self.assertEqual(response.status_code, HTTPStatus.OK)

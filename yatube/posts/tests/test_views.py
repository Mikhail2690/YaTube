import shutil
import tempfile

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from ..models import Follow, Group, Post
from ..forms import PostForm

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.post_author = User.objects.create_user(username='post-author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        names_templates_pages = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}): (
                'posts/group_list.html'
            ),
            reverse('posts:profile', kwargs={'username': 'author'}): (
                'posts/profile.html'
            ),
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}): (
                'posts/post_detail.html'
            ),
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}): (
                'posts/create_post.html'
            ),
        }
        for reverse_name, template in names_templates_pages.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_index_page_show_correct_context(self):
        """Шаблон страницы index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post = response.context['page_obj'][0]
        fields = {
            post.text: 'Тестовый пост',
            post.author: self.user,
            post.group: self.group,
            post.image: self.post.image
        }
        for field, expected_value in fields.items():
            with self.subTest(field=field):
                self.assertEqual(field, expected_value)

    def test_post_group_list_page_show_correct_context(self):
        """Шаблон страницы group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        context_post = {response.context['group'].title: self.group.title,
                        response.context['group'].description:
                        self.group.description,
                        response.context['group'].slug: self.group.slug,
                        response.context['post'].text: self.post.text,
                        response.context['post'].group: self.post.group,
                        response.context['post'].author: self.post.author,
                        response.context['post'].image: self.post.image,
                        }
        for value, expected_value in context_post.items():
            with self.subTest(value=value):
                self.assertEqual(context_post[value], expected_value)

    def test_profile_page_show_correct_context(self):
        """Шаблон страницы profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        context_post = {response.context['post'].text: self.post.text,
                        response.context['post'].group: self.post.group,
                        response.context['post'].author: self.post.author,
                        response.context['author']: self.user,
                        response.context['post'].image: self.post.image,
                        }
        for value, expected_value in context_post.items():
            with self.subTest(value=value):
                self.assertEqual(context_post[value], expected_value)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}))
        context_post = {response.context['post'].text: self.post.text,
                        response.context['post'].group: self.group,
                        response.context['post'].author: self.post.author,
                        response.context['post'].image: self.post.image,
                        }
        for value, expected in context_post.items():
            with self.subTest(value=value):
                self.assertEqual(context_post[value], expected)

    def test_post_create_page_and_post_edit_page_show_correct_context(self):
        """Шаблон post_create и post_edit
        сформированы с правильным контекстом.
        """
        reverse_names = [
            reverse('posts:post_create'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
        ]
        for reverse_name in reverse_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertIsInstance(response.context['form'], PostForm)
                if reverse_name == f'/posts/{self.post.pk}/edit/':
                    self.assertIn('is_edit', response.context)
                    self.assertIs(response.context['is_edit'], True)

    def test_post_was_not_included_another_group(self):
        """Проверка, что пост не появляется в группе
        к которой он не принадлежит.
        """
        new_group = Group.objects.create(
            title='Тестовая группа2',
            slug='test-group',
            description='Описание',
        )
        new_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group,
        )
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': new_group.slug}))
        context_post = response.context.get('page_obj')
        self.assertEqual(len(context_post), 0)
        self.assertNotIn(new_post, context_post)

    def test_index_cache(self):
        """Проверка, что страница index хранит записи в кеше"""
        cache_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост',
            group=self.group,
        )
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        cache_post.delete()
        new_response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertEqual(response.content, new_response.content)
        cache.clear()
        third_response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(response.content, third_response.content)

    def test_authorised_user_can_subscribe(self):
        """
        Авторизованный пользователь может подписываться на других
        пользователей.
        """
        self.authorized_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.post_author.username})
        )
        self.assertEqual(Follow.objects.count(), 1)

    def test_authorised_user_can_unsubscribe(self):
        """
        Авторизованный пользователь может удалять пользователей из подписок.
        """
        Follow.objects.create(
            user=self.user,
            author=self.post_author,
        )
        self.authorized_client.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.post_author.username})
        )
        self.assertEqual(Follow.objects.count(), 0)

    def test_new_post_in_correct_follow(self):
        """Новая запись автора появляется в ленте подписчиков."""
        Follow.objects.create(
            user=self.user,
            author=self.post_author,
        )
        new_post = Post.objects.create(
            author=self.post_author,
            text='Тестовый пост',
            group=self.group,
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(new_post, response.context['page_obj'])

    def test_new_post_does_not_appear_in_feed(self):
        """Новая запись не появляется в ленте тех, кто не подписан."""
        new_post = Post.objects.create(
            author=self.post_author,
            text='Тестовый пост',
            group=self.group,
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(new_post, response.context['page_obj'])

    def test_paginator_on_pages(self):
        """Проверка пагинации на страницах."""
        TEST_POST_COUNT = 13
        posts = (
            Post(
                author=self.user,
                text=f'Тестовый пост {index}',
                group=self.group) for index in range(1, TEST_POST_COUNT))
        Post.objects.bulk_create(posts)
        paginator_amount = 10
        second_page_amount = 3
        urls = (
            ('posts:index', None),
            ('posts:group_list', [PostViewsTests.group.slug]),
            ('posts:profile', [PostViewsTests.user.username]),
        )
        pages = (
            (1, paginator_amount),
            (2, second_page_amount),
        )
        for url_name, args in urls:
            for page, count in pages:
                with self.subTest(url_name=url_name):
                    response = self.authorized_client.get(
                        reverse(url_name, args=args), {'page': page})
                    self.assertEqual(
                        len(response.context.get('page_obj')), count)

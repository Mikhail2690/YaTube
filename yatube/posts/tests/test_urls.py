from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from http import HTTPStatus
from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост 1',
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_url_exists_at_desired_location(self):
        """Страницы доступные любому пользователю."""
        available_pages = [
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.user.username}/',
            f'/posts/{self.post.pk}/',
        ]
        for address in available_pages:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_list_url_exists_at_desired_location(self):
        """Страницы доступные авторизованному пользователю."""
        limited_pages = [
            f'/posts/{self.post.pk}/edit/',
            '/create/',
        ]
        for address in limited_pages:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_url_redirect_anonymous_on_login(self):
        """Страницы которые перенаправят анонимного
        пользователя на страницу логина.
        """
        limited_pages = [
            f'/posts/{self.post.pk}/edit/',
            '/create/',
        ]
        redirect_url = '/auth/login/?next='
        for address in limited_pages:
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, redirect_url + address)

    def test_unexisting_page_return_404(self):
        """Страница /unexisting_page/ вернет 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_non_author_cannot_edit_post(self):
        """Авторизованный юзер, но не автор,
        не может редактировать пост и получает редирект
        """
        not_author = User.objects.create_user(username='not author')
        not_author_client = Client()
        not_author_client.force_login(not_author)
        response = not_author_client.get(f'/posts/{self.post.pk}/edit/',
                                         follow=True)
        self.assertRedirects(response, f'/posts/{self.post.pk}/')

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        names_url_templates = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/page_not_found/': 'core/404.html',
        }
        for address, template in names_url_templates.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

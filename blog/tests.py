from django.contrib.auth import get_user_model
from django.urls import reverse

from blog.models import Post
from config.test_utils import CoursatyTestCase

User = get_user_model()

PASSWORD = "S3curePass!2026"


def make_post(author, title="A Blog Post", **kwargs):
    return Post.objects.create(
        author=author,
        title=title,
        excerpt="A short excerpt",
        body="The body of the post.",
        **kwargs,
    )


class PostListTests(CoursatyTestCase):
    def test_post_list_renders_all_posts(self):
        author = User.objects.create_user(
            username="author1", password=PASSWORD
        )
        make_post(author, "First Post")
        make_post(author, "Second Post")
        response = self.get(reverse("blog:post_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["posts"]), 2)

    def test_mine_filter_shows_only_own_posts(self):
        author = User.objects.create_user(
            username="author2", password=PASSWORD
        )
        other = User.objects.create_user(
            username="author3", password=PASSWORD
        )
        make_post(author, "Mine")
        make_post(other, "Theirs")
        self.client.force_login(author)
        response = self.get(
            reverse("blog:post_list"), data={"mine": "true"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["posts"]), 1)
        self.assertEqual(response.context["posts"][0].title, "Mine")


class PostDetailTests(CoursatyTestCase):
    def test_post_detail_renders(self):
        author = User.objects.create_user(
            username="author4", password=PASSWORD
        )
        post = make_post(author, "Readable Post")
        response = self.get(reverse("blog:post_detail", args=[post.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, post.title)


class PostCreateTests(CoursatyTestCase):
    def test_create_requires_login(self):
        response = self.get(reverse("blog:post_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_logged_in_user_can_create_post(self):
        author = User.objects.create_user(
            username="author5", password=PASSWORD
        )
        self.client.force_login(author)
        response = self.post(
            reverse("blog:post_create"),
            data={
                "title": "New Post",
                "excerpt": "Excerpt",
                "body": "Body text",
            },
        )
        self.assertEqual(response.status_code, 302)
        post = Post.objects.get(title="New Post")
        self.assertEqual(post.author, author)


class PostEditDeleteTests(CoursatyTestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            username="author6", password=PASSWORD
        )
        self.blog_post = make_post(self.author, "Editable Post")
        self.stranger = User.objects.create_user(
            username="stranger", password=PASSWORD
        )

    def test_author_can_edit(self):
        self.client.force_login(self.author)
        response = self.get(
            reverse("blog:post_edit", args=[self.blog_post.slug])
        )
        self.assertEqual(response.status_code, 200)

    def test_stranger_cannot_edit(self):
        self.client.force_login(self.stranger)
        response = self.get(
            reverse("blog:post_edit", args=[self.blog_post.slug])
        )
        self.assertEqual(response.status_code, 404)

    def test_stranger_cannot_delete(self):
        self.client.force_login(self.stranger)
        response = self.post(
            reverse("blog:post_delete", args=[self.blog_post.slug])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Post.objects.filter(pk=self.blog_post.pk).exists())

    def test_author_can_delete_via_post(self):
        self.client.force_login(self.author)
        response = self.post(
            reverse("blog:post_delete", args=[self.blog_post.slug])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.filter(pk=self.blog_post.pk).exists())

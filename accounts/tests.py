from django.contrib.auth import get_user_model
from django.urls import reverse

from config.test_utils import CoursatyTestCase

User = get_user_model()

PASSWORD = "S3curePass!2026"


class RegisterTests(CoursatyTestCase):
    def test_register_creates_user_and_logs_in(self):
        response = self.post(
            reverse("accounts:register"),
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_register_with_mismatched_passwords_fails(self):
        response = self.post(
            reverse("accounts:register"),
            data={
                "username": "newuser",
                "email": "new@example.com",
                "password1": PASSWORD,
                "password2": "DifferentPass!2026",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_authenticated_user_is_redirected(self):
        User.objects.create_user(username="existing", password=PASSWORD)
        self.client.force_login(User.objects.get(username="existing"))
        response = self.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 302)


class LoginTests(CoursatyTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="learner", password=PASSWORD
        )

    def test_valid_login_redirects_home(self):
        response = self.post(
            reverse("accounts:login"),
            data={"username": "learner", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")

    def test_invalid_login_shows_error(self):
        response = self.post(
            reverse("accounts:login"),
            data={"username": "learner", "password": "WrongPass!2026"},
        )
        self.assertEqual(response.status_code, 200)

    def test_next_parameter_is_preserved_through_post(self):
        response = self.get(reverse("accounts:login") + "?next=/courses/")
        self.assertContains(response, 'name="next"')
        response = self.post(
            reverse("accounts:login") + "?next=/courses/",
            data={"username": "learner", "password": PASSWORD, "next": "/courses/"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/courses/")

    def test_relative_next_is_honored(self):
        response = self.post(
            reverse("accounts:login"),
            data={
                "username": "learner",
                "password": PASSWORD,
                "next": "/courses/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/courses/")

    def test_external_next_is_rejected(self):
        response = self.post(
            reverse("accounts:login"),
            data={
                "username": "learner",
                "password": PASSWORD,
                "next": "https://evil.example.com/phish",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil", response["Location"])

    def test_protocol_relative_next_is_rejected(self):
        response = self.post(
            reverse("accounts:login"),
            data={
                "username": "learner",
                "password": PASSWORD,
                "next": "//evil.example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("evil", response["Location"])


class LogoutTests(CoursatyTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="loggerouter", password=PASSWORD
        )

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        response = self.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_logout_via_post_logs_out(self):
        self.client.force_login(self.user)
        response = self.post(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

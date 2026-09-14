from django.contrib.auth import get_user_model
from django.urls import reverse

from config.test_utils import CoursatyTestCase, make_course, make_lesson
from courses.models import Comment, Enrollment, Wishlist

User = get_user_model()

PASSWORD = "S3curePass!2026"


class HomeAndListTests(CoursatyTestCase):
    def test_home_renders(self):
        response = self.get(reverse("courses:home"))
        self.assertEqual(response.status_code, 200)

    def test_course_list_only_shows_published(self):
        make_course(title="Published Course")
        make_course(title="Hidden Course", is_published=False)
        response = self.get(reverse("courses:course_list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["courses"]), 1)

    def test_course_list_filters_by_category(self):
        from config.test_utils import make_category

        cat_a = make_category("Category Alpha")
        cat_b = make_category("Category Beta")
        make_course(title="Course A", category=cat_a)
        make_course(title="Course B", category=cat_b)
        response = self.get(
            reverse("courses:course_list"), data={"category": cat_a.slug}
        )
        self.assertEqual(len(response.context["courses"]), 1)
        self.assertEqual(response.context["courses"][0].title, "Course A")

    def test_course_list_search(self):
        make_course(title="Python Deep Dive")
        make_course(title="Woodworking Basics")
        response = self.get(reverse("courses:course_list"), data={"q": "python"})
        self.assertEqual(len(response.context["courses"]), 1)
        self.assertEqual(response.context["courses"][0].title, "Python Deep Dive")

    def test_course_list_ignores_invalid_rating(self):
        make_course(title="Rated Course")
        response = self.get(
            reverse("courses:course_list"), data={"rating": "not-a-number"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["courses"]), 1)

    def test_course_list_urlencodes_search_query_in_links(self):
        make_course(title="Ampersand Course")
        response = self.get(
            reverse("courses:course_list"), data={"q": "salt & pepper"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "q=salt%20%26%20pepper")


class CourseDetailTests(CoursatyTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="detailuser", password=PASSWORD
        )
        self.course = make_course(title="Detail Course")

    def test_published_course_renders(self):
        response = self.get(
            reverse("courses:course_detail", args=[self.course.slug])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/course_detail.html")

    def test_unpublished_course_404(self):
        course = make_course(title="Secret Course", is_published=False)
        response = self.get(reverse("courses:course_detail", args=[course.slug]))
        self.assertEqual(response.status_code, 404)

    def test_enrolled_user_gets_enrolled_template(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_login(self.user)
        response = self.get(
            reverse("courses:course_detail", args=[self.course.slug])
        )
        self.assertTemplateUsed(
            response, "courses/course_detail_enrolled.html"
        )


class LessonAccessTests(CoursatyTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="student", password=PASSWORD
        )
        self.course = make_course(title="Lesson Course")
        self.lesson = make_lesson(self.course)

    def test_anonymous_user_redirected_to_login(self):
        response = self.get(
            reverse(
                "courses:lesson", args=[self.course.slug, self.lesson.slug]
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_unenrolled_user_redirected_to_detail(self):
        self.client.force_login(self.user)
        response = self.get(
            reverse(
                "courses:lesson", args=[self.course.slug, self.lesson.slug]
            )
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("courses:course_detail", args=[self.course.slug]),
        )

    def test_enrolled_user_can_watch(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_login(self.user)
        response = self.get(
            reverse(
                "courses:lesson", args=[self.course.slug, self.lesson.slug]
            )
        )
        self.assertEqual(response.status_code, 200)


class CommentTests(CoursatyTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="commenter", password=PASSWORD
        )
        self.course = make_course(title="Comment Course")
        self.lesson = make_lesson(self.course)
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_login(self.user)
        self.url = reverse("courses:add_comment", args=[self.lesson.id])

    def test_enrolled_user_can_comment(self):
        response = self.post(self.url, data={"body": "Great lesson!"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)

    def test_reply_to_comment_on_same_lesson(self):
        parent = Comment.objects.create(
            user=self.user, lesson=self.lesson, body="Parent"
        )
        response = self.post(
            self.url, data={"body": "A reply", "parent_id": parent.id}
        )
        self.assertEqual(response.status_code, 302)
        reply = Comment.objects.get(body="A reply")
        self.assertEqual(reply.parent, parent)

    def test_missing_parent_is_rejected_without_error(self):
        response = self.post(
            self.url, data={"body": "Reply", "parent_id": 999999}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)

    def test_non_numeric_parent_is_rejected_without_error(self):
        response = self.post(
            self.url, data={"body": "Reply", "parent_id": "abc"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)

    def test_parent_from_other_lesson_is_rejected(self):
        other_course = make_course(title="Other Comment Course")
        other_lesson = make_lesson(other_course)
        foreign = Comment.objects.create(
            user=self.user, lesson=other_lesson, body="Foreign"
        )
        response = self.post(
            self.url, data={"body": "Reply", "parent_id": foreign.id}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 1)  # only the foreign one

    def test_unenrolled_user_cannot_comment(self):
        other = User.objects.create_user(
            username="stranger", password=PASSWORD
        )
        self.client.force_login(other)
        response = self.post(self.url, data={"body": "Sneaky comment"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)


class WishlistTests(CoursatyTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="saver", password=PASSWORD
        )
        self.course = make_course(title="Wishlist Course")
        self.client.force_login(self.user)
        self.url = reverse("courses:toggle_wishlist", args=[self.course.slug])

    def test_get_request_is_rejected(self):
        response = self.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_post_toggles_wishlist(self):
        response = self.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["saved"])
        self.assertTrue(Wishlist.objects.exists())

        response = self.post(self.url)
        self.assertFalse(response.json()["saved"])
        self.assertFalse(Wishlist.objects.exists())


class DashboardTests(CoursatyTestCase):
    def test_anonymous_user_redirected_to_login(self):
        response = self.get(reverse("courses:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_dashboard_lists_enrollments(self):
        user = User.objects.create_user(
            username="dashuser", password=PASSWORD
        )
        course = make_course(title="Dashboard Course")
        Enrollment.objects.create(user=user, course=course)
        self.client.force_login(user)
        response = self.get(reverse("courses:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["enrollments"]), 1)

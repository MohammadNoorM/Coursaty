"""Shared helpers for the project's test suite."""
import base64
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

# A minimal valid 1x1 transparent PNG.
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    },
)
class CoursatyTestCase(TestCase):
    """Base class for project tests.

    - Sends requests over HTTPS, matching production where
      SECURE_SSL_REDIRECT is active (DEBUG=False).
    - Keeps uploaded files in memory instead of uploading them to
      Cloudinary.
    """

    def get(self, url, **kwargs):
        return self.client.get(url, secure=True, **kwargs)

    def post(self, url, **kwargs):
        return self.client.post(url, secure=True, **kwargs)


def make_category(name="Web Development"):
    from courses.models import Category

    return Category.objects.create(name=name)


def make_course(**kwargs):
    from courses.models import Course

    defaults = {
        "title": "Test Course",
        "short_description": "A short description",
        "description": "A longer description",
        "what_you_learn": "Everything worth knowing",
        "requirements": "A computer",
        "price": Decimal("19.99"),
        "thumbnail": SimpleUploadedFile(
            "t.png", PNG_1PX, content_type="image/png"
        ),
        "is_published": True,
    }
    defaults.update(kwargs)
    if "category" not in defaults:
        defaults["category"] = make_category()
    return Course.objects.create(**defaults)


def make_lesson(course, title="Intro Lesson", order=0):
    from unittest import mock

    from django.core.files.storage import InMemoryStorage

    from courses.models import Lesson, Section

    section = Section.objects.create(course=course, title="Section 1")
    # Lesson.video declares a field-level Cloudinary storage that would
    # upload to the real service during tests; bypass it for the insert.
    video_field = Lesson._meta.get_field("video")
    with mock.patch.object(video_field, "storage", InMemoryStorage()):
        return Lesson.objects.create(
            section=section,
            title=title,
            order=order,
            video=SimpleUploadedFile("v.mp4", b"fake-video-bytes"),
        )

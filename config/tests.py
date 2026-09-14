"""Project-wide smoke tests: stylesheet build and template wiring."""
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.urls import reverse

from config.test_utils import CoursatyTestCase


class StylesheetLinkTests(CoursatyTestCase):
    """Pages must load the compiled stylesheet, not the Tailwind CDN."""

    def test_public_pages_use_built_stylesheet(self):
        pages = [
            "/",
            reverse("courses:course_list"),
            reverse("accounts:login"),
            reverse("accounts:register"),
            reverse("blog:post_list"),
        ]
        for url in pages:
            with self.subTest(url=url):
                response = self.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, "css/tailwind.css")
                self.assertNotContains(response, "cdn.tailwindcss.com")


class BuiltStylesheetTests(SimpleTestCase):
    """The compiled CSS must contain the shared design-system classes.

    These classes used to live in inline <style> blocks that were broken
    whenever a template used a class defined only in the *other* base
    template (e.g. ghost-border on the dashboard). The single built
    stylesheet fixes that; these checks keep it fixed.
    """

    REQUIRED_CLASSES = [
        ".material-symbols-outlined",
        ".glass-header",
        ".glass-panel",
        ".primary-gradient",
        ".signature-texture",
        ".ghost-border",
        ".editorial-shadow",
        # Scopes the underlined form style; if this class disappears from
        # the CSS, check that base_minimal.html's <body> still carries it
        # (Tailwind tree-shakes @layer rules for unknown selector classes).
        ".page-minimal",
    ]

    def test_built_css_contains_design_system_classes(self):
        css_path = Path(settings.BASE_DIR, "static", "css", "tailwind.css")
        if not css_path.exists():
            self.skipTest(
                "Built stylesheet not found - run 'python scripts/build_css.py'"
            )
        css = css_path.read_text(encoding="utf-8")
        for css_class in self.REQUIRED_CLASSES:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, css)

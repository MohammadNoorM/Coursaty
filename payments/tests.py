import hashlib
import hmac
import json
import time
from decimal import Decimal
from unittest import mock

import stripe
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse

from config.test_utils import CoursatyTestCase, make_course
from courses.models import Enrollment
from payments.models import Payment

User = get_user_model()

WEBHOOK_SECRET = "whsec_test"


class CheckoutTests(CoursatyTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="buyer", password="S3curePass!2026"
        )
        self.course = make_course(title="Stripe Course")

    def test_checkout_requires_login(self):
        response = self.get(reverse("payments:checkout", args=[self.course.slug]))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_checkout_creates_pending_payment_and_redirects_to_stripe(self):
        self.client.force_login(self.user)
        fake_session = mock.Mock(
            id="cs_test_123", url="https://checkout.stripe.com/pay/cs_test_123"
        )
        with mock.patch(
            "stripe.checkout.Session.create", return_value=fake_session
        ) as create:
            response = self.post(
                reverse("payments:checkout", args=[self.course.slug])
            )

        create.assert_called_once()
        kwargs = create.call_args.kwargs
        self.assertEqual(
            kwargs["line_items"][0]["price_data"]["unit_amount"], 1999
        )
        self.assertEqual(
            kwargs["metadata"],
            {"user_id": self.user.id, "course_id": self.course.id},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], fake_session.url)

        payment = Payment.objects.get()
        self.assertEqual(payment.status, "pending")
        self.assertEqual(payment.stripe_session_id, "cs_test_123")
        self.assertEqual(payment.amount, Decimal("19.99"))
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.course, self.course)

    def test_already_enrolled_skips_stripe(self):
        Enrollment.objects.create(user=self.user, course=self.course)
        self.client.force_login(self.user)
        with mock.patch("stripe.checkout.Session.create") as create:
            response = self.post(
                reverse("payments:checkout", args=[self.course.slug])
            )
        create.assert_not_called()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Payment.objects.exists())

    def test_unpublished_course_returns_404(self):
        course = make_course(title="Draft Course", is_published=False)
        self.client.force_login(self.user)
        response = self.post(reverse("payments:checkout", args=[course.slug]))
        self.assertEqual(response.status_code, 404)

    def test_stripe_error_is_handled_gracefully(self):
        self.client.force_login(self.user)
        with mock.patch(
            "stripe.checkout.Session.create",
            side_effect=stripe.StripeError("api down"),
        ):
            response = self.post(
                reverse("payments:checkout", args=[self.course.slug])
            )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Payment.objects.exists())


@override_settings(STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET)
class WebhookTests(CoursatyTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="webhookuser", password="S3curePass!2026"
        )
        self.course = make_course(title="Webhook Course")

    @staticmethod
    def _event(
        event_type,
        session_id="cs_test_123",
        payment_status="paid",
        user_id=None,
        course_id=None,
        include_metadata=True,
    ):
        session = {"id": session_id, "payment_status": payment_status}
        if include_metadata:
            session["metadata"] = {}
            if user_id is not None:
                session["metadata"]["user_id"] = str(user_id)
            if course_id is not None:
                session["metadata"]["course_id"] = str(course_id)
        return {
            "id": "evt_test_1",
            "object": "event",
            "type": event_type,
            "data": {"object": session},
        }

    def _post_signed(self, event, secret=WEBHOOK_SECRET):
        payload = json.dumps(event).encode()
        timestamp = int(time.time())
        signed = str(timestamp).encode() + b"." + payload
        signature = hmac.new(
            secret.encode(), signed, hashlib.sha256
        ).hexdigest()
        return self.post(
            reverse("payments:webhook"),
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=%d,v1=%s" % (timestamp, signature),
        )

    def _pending_payment(self, session_id="cs_test_123"):
        return Payment.objects.create(
            user=self.user,
            course=self.course,
            stripe_session_id=session_id,
            amount=Decimal("19.99"),
            status="pending",
        )

    def test_invalid_signature_returns_400(self):
        payment = self._pending_payment()
        response = self._post_signed(
            self._event(
                "checkout.session.completed",
                user_id=self.user.id,
                course_id=self.course.id,
            ),
            secret="whsec_wrong",
        )
        self.assertEqual(response.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")
        self.assertFalse(Enrollment.objects.exists())

    def test_invalid_json_returns_400(self):
        payload = b"this is not json"
        timestamp = int(time.time())
        signed = str(timestamp).encode() + b"." + payload
        signature = hmac.new(
            WEBHOOK_SECRET.encode(), signed, hashlib.sha256
        ).hexdigest()
        response = self.post(
            reverse("payments:webhook"),
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="t=%d,v1=%s" % (timestamp, signature),
        )
        self.assertEqual(response.status_code, 400)

    def test_completed_event_fulfills_order(self):
        payment = self._pending_payment()
        response = self._post_signed(
            self._event(
                "checkout.session.completed",
                user_id=self.user.id,
                course_id=self.course.id,
            )
        )
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "completed")
        self.assertTrue(
            Enrollment.objects.filter(
                user=self.user, course=self.course
            ).exists()
        )

    def test_fulfillment_is_idempotent(self):
        self._pending_payment()
        event = self._event(
            "checkout.session.completed",
            user_id=self.user.id,
            course_id=self.course.id,
        )
        self._post_signed(event)
        self._post_signed(event)
        self.assertEqual(Enrollment.objects.count(), 1)

    def test_session_without_metadata_is_ignored(self):
        payment = self._pending_payment()
        response = self._post_signed(
            self._event("checkout.session.completed", include_metadata=False)
        )
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")
        self.assertFalse(Enrollment.objects.exists())

    def test_unpaid_session_is_ignored(self):
        payment = self._pending_payment()
        response = self._post_signed(
            self._event(
                "checkout.session.completed",
                payment_status="processing",
                user_id=self.user.id,
                course_id=self.course.id,
            )
        )
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")
        self.assertFalse(Enrollment.objects.exists())

    def test_deleted_user_is_ignored(self):
        payment = self._pending_payment()
        response = self._post_signed(
            self._event(
                "checkout.session.completed",
                user_id=424242,
                course_id=self.course.id,
            )
        )
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")
        self.assertFalse(Enrollment.objects.exists())

    def test_expired_event_marks_payment_failed(self):
        payment = self._pending_payment()
        response = self._post_signed(
            self._event("checkout.session.expired")
        )
        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "failed")


class PaymentSuccessTests(CoursatyTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="successuser", password="S3curePass!2026"
        )
        self.course = make_course(title="Success Course")

    def _payment(self, status="pending", session_id="cs_test_123", user=None):
        return Payment.objects.create(
            user=user or self.user,
            course=self.course,
            stripe_session_id=session_id,
            amount=Decimal("19.99"),
            status=status,
        )

    def _success_url(self, session_id=None):
        url = reverse("payments:success")
        if session_id:
            url += "?session_id=%s" % session_id
        return url

    def test_missing_session_id_redirects_home(self):
        self.client.force_login(self.user)
        response = self.get(self._success_url())
        self.assertEqual(response.status_code, 302)

    def test_unknown_session_id_redirects_home(self):
        self.client.force_login(self.user)
        response = self.get(self._success_url("bogus"))
        self.assertEqual(response.status_code, 302)

    def test_pending_payment_is_confirmed_via_stripe_api(self):
        payment = self._payment()
        self.client.force_login(self.user)
        fake_session = {
            "id": "cs_test_123",
            "payment_status": "paid",
            "metadata": {
                "user_id": str(self.user.id),
                "course_id": str(self.course.id),
            },
        }
        with mock.patch(
            "stripe.checkout.Session.retrieve", return_value=fake_session
        ):
            response = self.get(self._success_url("cs_test_123"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "payments/payment.html")
        payment.refresh_from_db()
        self.assertEqual(payment.status, "completed")
        self.assertTrue(
            Enrollment.objects.filter(
                user=self.user, course=self.course
            ).exists()
        )

    def test_unpaid_session_redirects_home(self):
        payment = self._payment()
        self.client.force_login(self.user)
        fake_session = {
            "id": "cs_test_123",
            "payment_status": "unpaid",
            "metadata": {
                "user_id": str(self.user.id),
                "course_id": str(self.course.id),
            },
        }
        with mock.patch(
            "stripe.checkout.Session.retrieve", return_value=fake_session
        ):
            response = self.get(self._success_url("cs_test_123"))
        self.assertEqual(response.status_code, 302)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")
        self.assertFalse(Enrollment.objects.exists())

    def test_completed_payment_renders_success_page(self):
        self._payment(status="completed")
        self.client.force_login(self.user)
        response = self.get(self._success_url("cs_test_123"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)

    def test_other_users_payment_is_not_visible(self):
        other = User.objects.create_user(
            username="otheruser", password="S3curePass!2026"
        )
        self._payment(user=other)
        self.client.force_login(self.user)
        response = self.get(self._success_url("cs_test_123"))
        self.assertEqual(response.status_code, 302)

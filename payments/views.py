import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from courses.models import Course, Enrollment
from .models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY


def _get(obj, key, default=None):
    """Read a key from a Stripe object or dict without raising."""
    try:
        value = obj[key]
    except (KeyError, IndexError):
        return default
    return default if value is None else value


@login_required
def create_checkout_session(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug, is_published=True)

    # Already enrolled? Go straight to course detail page
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, _('You are already enrolled in this course.'))
        return redirect('courses:course_detail', slug=course_slug)

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': course.title,
                    },
                    'unit_amount': int(course.price * 100),  # cents
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri('/payments/success/') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri('/payments/cancel/'),
            metadata={
                'user_id': request.user.id,
                'course_id': course.id,
            }
        )
    except stripe.StripeError:
        messages.error(request, _('Could not start the payment session. Please try again.'))
        return redirect('courses:course_detail', slug=course_slug)

    # Create a pending payment record
    Payment.objects.create(
        user=request.user,
        course=course,
        stripe_session_id=session.id,
        amount=course.price,
        status='pending'
    )

    return redirect(session.url)


@login_required
def payment_success(request):
    session_id = request.GET.get('session_id')
    payment = None

    if session_id:
        payment = Payment.objects.filter(
            stripe_session_id=session_id, user=request.user
        ).first()

        if payment and payment.status != 'completed':
            # The webhook may not have arrived yet; ask Stripe directly.
            try:
                session = stripe.checkout.Session.retrieve(session_id)
            except stripe.StripeError:
                session = None
            if session is not None and _get(session, 'payment_status') == 'paid':
                _fulfill_checkout(session)
                payment.refresh_from_db()

    if payment and payment.status == 'completed':
        return render(request, 'payments/payment.html',
                      {'course': payment.course, 'status': 'success'})

    messages.error(request, _('Payment not confirmed yet. Please wait a moment.'))
    return redirect('courses:home')


@login_required
def payment_cancel(request):
    messages.warning(request, _('Payment was cancelled. You can try again.'))
    return render(request, 'payments/payment.html', {'status': 'cancel'})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.SignatureVerificationError):
        # Invalid payload or invalid/missing signature
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        _fulfill_checkout(event['data']['object'])
    elif event['type'] == 'checkout.session.expired':
        Payment.objects.filter(
            stripe_session_id=_get(event['data']['object'], 'id'),
            status='pending',
        ).update(status='failed')

    return HttpResponse(status=200)


def _fulfill_checkout(session):
    """Mark the payment complete and enroll the buyer (idempotent).

    Accepts a checkout session from either a webhook event or the
    Stripe API. Sessions without metadata (not created by this site)
    or referencing deleted users/courses are ignored so the webhook
    always returns 200 and Stripe does not retry forever.
    """
    if _get(session, 'payment_status') != 'paid':
        return

    metadata = _get(session, 'metadata') or {}
    user_id = _get(metadata, 'user_id')
    course_id = _get(metadata, 'course_id')
    if not user_id or not course_id:
        return

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        course = Course.objects.get(pk=course_id)
    except (User.DoesNotExist, Course.DoesNotExist, ValueError):
        return

    Payment.objects.filter(
        stripe_session_id=_get(session, 'id')
    ).update(status='completed')
    Enrollment.objects.get_or_create(user=user, course=course)

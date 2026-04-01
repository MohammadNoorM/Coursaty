import stripe, json
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.http import HttpResponse
from courses.models import Course, Enrollment
from .models import Payment

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def create_checkout_session(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug, is_published=True)

    # Already enrolled? Go straight to course detail page
    if Enrollment.objects.filter(user=request.user, course=course).exists():
        messages.info(request, 'You are already enrolled in this course.')
        return redirect('courses:course_detail', slug=course_slug)

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': course.title,
                },
                'unit_amount': int(course.price * 100), # cents
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=request.build_absolute_uri(f'/payments/success/?session_id={{CHECKOUT_SESSION_ID}}'),
        cancel_url=request.build_absolute_uri(f'/payments/cancel/'),
        metadata={
            'user_id': request.user.id,
            'course_id': course.id,
        }
    )

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
    payment = Payment.objects.filter(stripe_session_id=session_id, user=request.user).first()

    if payment and payment.status == 'completed':
        return render(request, 'payments/success.html', {'course': payment.course})
    
    messages.error(request, 'Payment not confirmed yet. Please wait a moment.')
    return redirect('courses:home')


@login_required
def payment_cancel(request):
    messages.warning(request, 'Payment was cancelled. You can try again.')
    return render(request, 'payments/cancel.html')

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['metadata']['user_id']
        course_id = session['metadata']['course_id']

        # Update payment status
        Payment.objects.filter(stripe_session_id=session['id']).update(status='completed')

        # Create enrollment
        Enrollment.objects.get_or_create(user_id=user_id, course_id=course_id)

    return HttpResponse(status=200)
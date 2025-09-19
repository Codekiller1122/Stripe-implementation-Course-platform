import os, stripe, json, uuid
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from rest_framework.decorators import api_view
from .models import Course, Enrollment
from .serializers import CourseSerializer, EnrollmentSerializer

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['GET'])
def courses_list(request):
    qs = Course.objects.all().order_by('-created_at')
    return JsonResponse(CourseSerializer(qs, many=True).data, safe=False)

@api_view(['GET'])
def course_detail(request, slug):
    c = get_object_or_404(Course, slug=slug)
    return JsonResponse(CourseSerializer(c).data, safe=False)

@api_view(['POST'])
def create_checkout_session(request):
    data = request.data
    course_id = data.get('course_id')
    student_email = data.get('email')
    # optional: connected account id for instructor split
    connected_account = data.get('instructor_account')  # stripe account id
    course = get_object_or_404(Course, id=course_id)
    domain = settings.PUBLIC_BASE_URL.rstrip('/')
    # line item price data
    if course.price_cents <= 0:
        return JsonResponse({'error':'course is free'}, status=400)
    # You can also pre-create a Price object in Stripe and reference price id instead
    try:
        checkout_data = {
            'success_url': f'{domain}/checkout/success/?session_id={{CHECKOUT_SESSION_ID}}',
            'cancel_url': f'{domain}/checkout/cancel/',
            'payment_method_types': ['card'],
            'mode': 'payment',
            'line_items': [{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': course.price_cents,
                    'product_data': {'name': course.title},
                },
                'quantity': 1,
            }],
            'customer_email': student_email,
            'metadata': {'course_id': str(course.id), 'student_email': student_email},
        }
        if connected_account:
            # Route funds to connected account using transfer_data (platform keeps application_fee_amount)
            checkout_data['payment_intent_data'] = {'transfer_data': {'destination': connected_account}, 'application_fee_amount': int(course.price_cents * 0.10)}
        session = stripe.checkout.Session.create(**checkout_data)
        return JsonResponse({'url': session.url, 'id': session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
def create_payment_intent(request):
    data = request.data
    amount = data.get('amount')  # float or cents
    currency = data.get('currency', 'usd')
    try:
        amount_cents = int(float(amount) * 100)
    except:
        amount_cents = int(amount or 0)
    try:
        intent = stripe.PaymentIntent.create(amount=amount_cents, currency=currency, payment_method_types=['card'], metadata=data.get('metadata', {}))
        return JsonResponse({'client_secret': intent.client_secret, 'id': intent.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['POST'])
def create_subscription_checkout(request):
    data = request.data
    price_id = data.get('price_id')  # prefer existing price in Stripe
    customer_email = data.get('email')
    trial_days = int(data.get('trial_days', 0) or 0)
    domain = settings.PUBLIC_BASE_URL.rstrip('/')
    try:
        session = stripe.checkout.Session.create(
            success_url=f'{domain}/checkout/success/?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{domain}/checkout/cancel/',
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{'price': price_id, 'quantity': 1}],
            customer_email=customer_email,
            subscription_data = {'trial_period_days': trial_days} if trial_days>0 else {}
        )
        return JsonResponse({'url': session.url, 'id': session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(['GET'])
def enrollments_list(request):
    qs = Enrollment.objects.all().order_by('-created_at')[:200]
    return JsonResponse(EnrollmentSerializer(qs, many=True).data, safe=False)

# ------------------ Extended Stripe Features ------------------
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

@api_view(['POST'])
def create_connect_account(request):
    '''Create a Stripe Express account and return account id.'''
    data = request.data
    country = data.get('country', 'US')
    try:
        acct = stripe.Account.create(type='express', country=country, capabilities={'card_payments': {'requested': True}, 'transfers': {'requested': True}})
        return JsonResponse({'account_id': acct.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['GET'])
def create_connect_onboarding_link(request):
    '''Create an account link for onboarding for a given account_id'''
    account_id = request.GET.get('account_id')
    if not account_id:
        return JsonResponse({'error':'account_id required'}, status=400)
    domain = settings.PUBLIC_BASE_URL.rstrip('/')
    try:
        link = stripe.Account.create_login_link(account_id)
        return JsonResponse({'url': link.url})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['POST'])
def create_setup_intent(request):
    '''Create a SetupIntent to save a payment method for a customer across payments.'''
    email = request.data.get('email')
    # In production, create or lookup a Stripe Customer for this email and persist mapping.
    try:
        customer = stripe.Customer.create(email=email)
        si = stripe.SetupIntent.create(customer=customer.id, payment_method_types=['card'])
        return JsonResponse({'client_secret': si.client_secret, 'customer': customer.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['POST'])
def manage_customer_portal(request):
    '''Create a Stripe Billing customer portal session for a customer (customer_id required).'''
    customer_id = request.data.get('customer_id')
    return_url = settings.PUBLIC_BASE_URL
    try:
        session = stripe.billing_portal.Session.create(customer=customer_id, return_url=return_url)
        return JsonResponse({'url': session.url})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['POST'])
def cancel_subscription(request):
    subscription_id = request.data.get('subscription_id')
    try:
        sub = stripe.Subscription.delete(subscription_id)
        return JsonResponse({'status':'cancelled', 'id': sub.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@api_view(['POST'])
def apply_coupon_and_create_checkout(request):
    '''Create a checkout session with optional coupon code. Coupon must exist in Stripe.'''
    data = request.data
    price_id = data.get('price_id')
    email = data.get('email')
    coupon = data.get('coupon')  # coupon id in Stripe or coupon object
    domain = settings.PUBLIC_BASE_URL.rstrip('/')
    try:
        session_data = {
            'success_url': f'{domain}/checkout/success/?session_id={{CHECKOUT_SESSION_ID}}',
            'cancel_url': f'{domain}/checkout/cancel/',
            'payment_method_types': ['card'],
            'mode': 'subscription' if price_id and price_id.startswith('price_') else 'payment',
            'line_items': [{'price': price_id, 'quantity':1}] if price_id else [],
            'customer_email': email,
        }
        if coupon:
            session_data['discounts'] = [{'coupon': coupon}]
        session = stripe.checkout.Session.create(**session_data)
        return JsonResponse({'url': session.url, 'id': session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

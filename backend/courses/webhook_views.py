import stripe, json, os
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Course, Enrollment
stripe.api_key = settings.STRIPE_SECRET_KEY
# You should set STRIPE_WEBHOOK_SECRET in your env for verifying signatures in production
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET','')

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    event = None
    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except ValueError as e:
            return HttpResponse(status=400)
        except stripe.error.SignatureVerificationError as e:
            return HttpResponse(status=400)
    else:
        try:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        except Exception:
            return HttpResponse(status=400)
    # Handle the event
    kind = event['type']
    data = event['data']['object']
    try:
        if kind == 'checkout.session.completed':
            # Payment is complete, create enrollment
            metadata = data.get('metadata', {})
            course_id = metadata.get('course_id') or data.get('metadata', {}).get('course_id')
            student_email = metadata.get('student_email') or data.get('customer_email') or data.get('customer', '')
            payment_intent = data.get('payment_intent')
            # get charge id via PaymentIntent if available
            charge_id = None
            try:
                pi = stripe.PaymentIntent.retrieve(payment_intent)
                if pi.charges and len(pi.charges.data)>0:
                    charge_id = pi.charges.data[0].id
            except Exception:
                pass
            if course_id:
                try:
                    course = Course.objects.get(id=int(course_id))
                    Enrollment.objects.create(course=course, student_email=student_email, stripe_customer_id=data.get('customer'), amount_paid= int((data.get('amount_total') or 0)), currency=data.get('currency') or 'usd', payment_intent_id=payment_intent, charge_id=charge_id)
                except Course.DoesNotExist:
                    pass
        elif kind == 'invoice.paid':
            # subscription payments or invoices succeeded
            pass
        elif kind == 'invoice.payment_failed':
            # handle failed payments
            pass
        elif kind == 'charge.refunded':
            # handle refunds: deactivate enrollment if refund covers charge
            charge = data
            # try to find enrollment with charge_id
            Enrollment.objects.filter(charge_id=charge.get('id')).update(active=False)
        # handle connect.payout.created, transfer.updated etc for payouts to instructors
    except Exception as e:
        # log error
        print('Webhook handler error', e)
    return JsonResponse({'status':'ok'})

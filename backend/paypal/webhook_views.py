import os, json, requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import Donation, Subscription, Payout

# basic webhook receiver - in production verify transmission via PayPal webhook-ID and signatures
@csrf_exempt
def paypal_webhook(request):
    try:
        event = json.loads(request.body.decode())
    except Exception as e:
        return HttpResponse(status=400)
    kind = event.get('event_type')
    data = event.get('resource', {})
    # handle common events
    if kind == 'CHECKOUT.ORDER.APPROVED' or kind == 'PAYMENT.CAPTURE.COMPLETED':
        order_id = data.get('id') or data.get('supplementary_data', {}).get('related_ids', {}).get('order_id')
        # mark donation captured if exists
        if order_id:
            Donation.objects.filter(paypal_order_id=order_id).update(status='captured')
    elif kind == 'BILLING.SUBSCRIPTION.ACTIVATED' or kind == 'BILLING.SUBSCRIPTION.CREATED':
        sub_id = data.get('id')
        Subscription.objects.filter(paypal_subscription_id=sub_id).update(status=data.get('status','active'))
    elif kind == 'PAYMENT.PAYOUTSBATCH.DENIED' or kind == 'PAYMENT.PAYOUTSBATCH.SUCCESS':
        batch_id = data.get('batch_header', {}).get('payout_batch_id')
        if batch_id:
            Payout.objects.filter(paypal_batch_id=batch_id).update(status=data.get('batch_header', {}).get('batch_status',''))
    # respond 200
    return JsonResponse({'status':'ok'})

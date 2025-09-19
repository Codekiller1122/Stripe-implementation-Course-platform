import os, requests, base64, json
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from rest_framework.decorators import api_view
from .models import Campaign, Donation, Subscription, Payout
from .serializers import CampaignSerializer, DonationSerializer, SubscriptionSerializer, PayoutSerializer

# PayPal helper: get access token
def paypal_token():
    client = settings.PAYPAL_CLIENT_ID
    secret = settings.PAYPAL_SECRET
    auth = (client + ':' + secret).encode()
    headers = {'Accept':'application/json','Accept-Language':'en_US'}
    data = {'grant_type':'client_credentials'}
    resp = requests.post(f'{settings.PAYPAL_API_BASE}/v1/oauth2/token', data=data, headers=headers, auth=(settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET))
    if resp.status_code==200:
        return resp.json().get('access_token')
    return None

@api_view(['GET'])
def campaigns_list(request):
    qs = Campaign.objects.all().order_by('-created_at')
    return JsonResponse(CampaignSerializer(qs, many=True).data, safe=False)

@api_view(['POST'])
def create_order(request):
    '''Create a PayPal Order for a one-time donation and return approval link.'''
    data = request.data
    campaign_id = data.get('campaign_id')
    email = data.get('email')
    amount = float(data.get('amount',0))
    campaign = get_object_or_404(Campaign, id=campaign_id)
    token = paypal_token()
    if not token:
        return JsonResponse({'error':'paypal token failed'}, status=500)
    headers = {'Content-Type':'application/json','Authorization':f'Bearer {token}'}
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code":"USD","value": f"{amount:.2f}"},
            "payee": {"email_address": os.environ.get('PLATFORM_PAYPAL_EMAIL','')},
            "custom_id": str(campaign.id),
            "description": f"Donation to {campaign.title}"
        }],
        "application_context": {
            "return_url": f"{settings.PUBLIC_BASE_URL}/api/paypal/capture-order/",
            "cancel_url": f"{settings.PUBLIC_BASE_URL}/donate/cancel/"
        }
    }
    r = requests.post(f'{settings.PAYPAL_API_BASE}/v2/checkout/orders', headers=headers, json=payload)
    if r.status_code>=400:
        return JsonResponse({'error':'order create failed','details':r.text}, status=500)
    order = r.json()
    # create Donation record with status created
    amount_cents = int(round(amount*100))
    donation = Donation.objects.create(campaign=campaign, donor_email=email or '', amount_cents=amount_cents, paypal_order_id=order['id'], status='created')
    # find approval link
    approve = None
    for link in order.get('links',[]):
        if link.get('rel')=='approve':
            approve = link.get('href'); break
    return JsonResponse({'approve_url': approve, 'order_id': order['id']})

@api_view(['GET','POST'])
def capture_order(request):
    '''Capture PayPal order after buyer approves. PayPal will redirect user to return_url with token parameter.'''
    token = request.GET.get('token') or request.data.get('token')
    if not token:
        return JsonResponse({'error':'missing token'}, status=400)
    t = paypal_token()
    headers = {'Content-Type':'application/json','Authorization':f'Bearer {t}'}
    r = requests.post(f'{settings.PAYPAL_API_BASE}/v2/checkout/orders/{token}/capture', headers=headers)
    if r.status_code>=400:
        return JsonResponse({'error':'capture failed','details': r.text}, status=500)
    capture = r.json()
    # update Donation status to captured
    try:
        donation = Donation.objects.get(paypal_order_id=token)
        donation.status = 'captured'
        # set amount from capture if available
        try:
            amt = float(capture['purchase_units'][0]['payments']['captures'][0]['amount']['value'])
            donation.amount_cents = int(round(amt*100))
        except Exception:
            pass
        donation.save()
    except Donation.DoesNotExist:
        pass
    # return a simple success page or JSON
    return JsonResponse({'status':'captured','capture': capture})

@api_view(['POST'])
def create_subscription_plan(request):
    '''Create a PayPal product & plan for recurring donations, return approve link for subscription'''
    data = request.data
    campaign_id = data.get('campaign_id')
    email = data.get('email')
    amount = float(data.get('amount',0))
    campaign = get_object_or_404(Campaign, id=campaign_id)
    token = paypal_token()
    headers = {'Content-Type':'application/json','Authorization':f'Bearer {token}'}
    # create product
    prod_payload = {"name": f"Subscription for {campaign.title}", "type":"SERVICE"}
    prod_r = requests.post(f'{settings.PAYPAL_API_BASE}/v1/catalogs/products', headers=headers, json=prod_payload)
    if prod_r.status_code>=400:
        return JsonResponse({'error':'product create failed','details':prod_r.text}, status=500)
    product = prod_r.json()
    # create plan (monthly)
    plan_payload = {
        "product_id": product['id'],
        "name": f"{campaign.title} Monthly Donation",
        "billing_cycles": [{
            "frequency": {"interval_unit": "MONTH", "interval_count": 1},
            "tenure_type": "REGULAR",
            "sequence": 1,
            "total_cycles": 0,
            "pricing_scheme": {"fixed_price": {"value": f"{amount:.2f}", "currency_code": "USD"}}
        }],
        "payment_preferences": {"auto_bill_outstanding": True, "setup_fee": {"value":"0","currency_code":"USD"}, "wait_for_auto_bill_outstanding": False},
        "taxes": {"percentage":"0", "inclusive": False}
    }
    plan_r = requests.post(f'{settings.PAYPAL_API_BASE}/v1/billing/plans', headers=headers, json=plan_payload)
    if plan_r.status_code>=400:
        return JsonResponse({'error':'plan create failed','details':plan_r.text}, status=500)
    plan = plan_r.json()
    # create subscription
    sub_payload = {"plan_id": plan['id'], "subscriber": {"email_address": email}, "application_context": {"return_url": f"{settings.PUBLIC_BASE_URL}/api/paypal/subscription-return/", "cancel_url": f"{settings.PUBLIC_BASE_URL}/subscribe/cancel/" } }
    sub_r = requests.post(f'{settings.PAYPAL_API_BASE}/v1/billing/subscriptions', headers=headers, json=sub_payload)
    if sub_r.status_code>=400:
        return JsonResponse({'error':'subscription create failed','details':sub_r.text}, status=500)
    subscription = sub_r.json()
    # save subscription record (pending approval)
    sub = Subscription.objects.create(campaign=campaign, subscriber_email=email or '', paypal_subscription_id=subscription.get('id'), status='pending')
    # find approval link
    approve = None
    for link in subscription.get('links', []):
        if link.get('rel') == 'approve':
            approve = link.get('href'); break
    return JsonResponse({'approve_url': approve, 'subscription_id': subscription.get('id')})

@api_view(['GET','POST'])
def subscription_return(request):
    '''After user approves subscription, PayPal redirects. We can look up subscription and update status.'''
    token = request.GET.get('token') or request.data.get('token')
    if not token:
        return JsonResponse({'error':'missing token'}, status=400)
    # fetch subscription details
    t = paypal_token()
    headers = {'Content-Type':'application/json','Authorization':f'Bearer {t}'}
    r = requests.get(f'{settings.PAYPAL_API_BASE}/v1/billing/subscriptions/{token}', headers=headers)
    if r.status_code>=400:
        return JsonResponse({'error':'fetch subscription failed','details':r.text}, status=500)
    subs = r.json()
    # update Subscription status
    try:
        s = Subscription.objects.get(paypal_subscription_id=token)
        s.status = subs.get('status','active')
        s.save()
    except Subscription.DoesNotExist:
        pass
    return JsonResponse({'status':'subscription_updated','subscription': subs})

@api_view(['POST'])
def create_payout(request):
    '''Create a PayPal Payout to campaign owner (requires owner PayPal email).'''
    data = request.data
    campaign_id = data.get('campaign_id')
    amount = float(data.get('amount',0))
    campaign = get_object_or_404(Campaign, id=campaign_id)
    if not campaign.owner_email:
        return JsonResponse({'error':'campaign owner has no paypal email'}, status=400)
    token = paypal_token()
    headers = {'Content-Type':'application/json','Authorization':f'Bearer {token}'}
    batch_id = 'batch-' + str(uuid.uuid4())[:8]
    payout_payload = {
        "sender_batch_header": {"sender_batch_id": batch_id, "email_subject": f"Payout for {campaign.title}"},
        "items": [{"recipient_type": "EMAIL", "amount": {"value": f"{amount:.2f}", "currency":"USD"}, "receiver": campaign.owner_email, "note": f"Payout from {campaign.title}"}]
    }
    r = requests.post(f'{settings.PAYPAL_API_BASE}/v1/payments/payouts', headers=headers, json=payout_payload)
    if r.status_code>=400:
        return JsonResponse({'error':'payout failed','details': r.text}, status=500)
    resp = r.json()
    payout = Payout.objects.create(campaign=campaign, amount_cents=int(round(amount*100)), paypal_batch_id=resp.get('batch_header',{}).get('payout_batch_id'), status='pending')
    return JsonResponse({'status':'payout_created','batch': resp.get('batch_header')})

@api_view(['GET'])
def donations_list(request):
    qs = Donation.objects.all().order_by('-created_at')[:200]
    return JsonResponse(DonationSerializer(qs, many=True).data, safe=False)

@api_view(['GET'])
def subscriptions_list(request):
    qs = Subscription.objects.all().order_by('-created_at')[:200]
    return JsonResponse(SubscriptionSerializer(qs, many=True).data, safe=False)

@api_view(['GET'])
def payouts_list(request):
    qs = Payout.objects.all().order_by('-created_at')[:200]
    return JsonResponse(PayoutSerializer(qs, many=True).data, safe=False)

from django.urls import path
from . import views, webhook_views
urlpatterns = [
    path('campaigns/', views.campaigns_list),
    path('donations/', views.donations_list),
    path('subscriptions/', views.subscriptions_list),
    path('payouts/', views.payouts_list),
    path('paypal/create-order/', views.create_order),
    path('paypal/capture-order/', views.capture_order),
    path('paypal/create-subscription/', views.create_subscription_plan),
    path('paypal/subscription-return/', views.subscription_return),
    path('paypal/create-payout/', views.create_payout),
    path('paypal/create-order/approve/', views.create_order),  # alias
    # webhook endpoint
    path('paypal/webhook/', webhook_views.paypal_webhook),
]

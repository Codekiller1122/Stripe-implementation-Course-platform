from django.urls import path
from . import views

urlpatterns = [
    path('courses/', views.courses_list),
    path('courses/<slug:slug>/', views.course_detail),
    path('enrollments/', views.enrollments_list),
    path('payments/create-checkout-session/', views.create_checkout_session),
    path('payments/create-payment-intent/', views.create_payment_intent),
    path('payments/create-subscription-checkout/', views.create_subscription_checkout),
path('stripe/create-connect-account/', views.create_connect_account),
path('stripe/create-connect-onboard/', views.create_connect_onboarding_link),
path('stripe/create-setup-intent/', views.create_setup_intent),
path('stripe/create-portal-session/', views.manage_customer_portal),
path('stripe/cancel-subscription/', views.cancel_subscription),
path('stripe/create-checkout-with-coupon/', views.apply_coupon_and_create_checkout),

]

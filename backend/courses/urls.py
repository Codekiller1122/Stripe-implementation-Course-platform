from django.urls import path
from . import views

urlpatterns = [
    path('courses/', views.courses_list),
    path('courses/<slug:slug>/', views.course_detail),
    path('enrollments/', views.enrollments_list),
    path('payments/create-checkout-session/', views.create_checkout_session),
    path('payments/create-payment-intent/', views.create_payment_intent),
    path('payments/create-subscription-checkout/', views.create_subscription_checkout),
]

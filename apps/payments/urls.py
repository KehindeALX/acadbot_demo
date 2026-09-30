"""
URL configuration for the Payments app.
"""
from django.urls import path

from .views import initialize_payment, payment_status, verify_payment, PaystackWebhook

urlpatterns = [
    path('initialize/', initialize_payment, name='payments-initialize'),
    path('verify/', verify_payment, name='payments-verify'),
    path('status/', payment_status, name='payments-status'),
    path('webhook/', PaystackWebhook.as_view(), name='payments-webhook'),
]

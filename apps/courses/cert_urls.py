"""
URL configuration for certificates, mounted at /api/certificates/.
"""
from django.urls import path

from .certificates import (
    list_certificates,
    certificate_pdf,
    verify_certificate,
)

urlpatterns = [
    path('', list_certificates, name='certificate-list'),
    path('verify/<str:code>/', verify_certificate, name='certificate-verify'),
    path('<str:code>/pdf/', certificate_pdf, name='certificate-pdf'),
]

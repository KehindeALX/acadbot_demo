from django.urls import path

from .views import guide_chat

urlpatterns = [
    path('chat/', guide_chat, name='guide-chat'),
]

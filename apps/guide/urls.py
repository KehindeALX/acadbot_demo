from django.urls import path

from .speakpro_views import speakpro_analyze, speakpro_feedback
from .views import guide_chat

urlpatterns = [
    path('chat/', guide_chat, name='guide-chat'),
    path('speakpro/analyze/', speakpro_analyze, name='speakpro-analyze'),
    path('speakpro/feedback/', speakpro_feedback, name='speakpro-feedback'),
]

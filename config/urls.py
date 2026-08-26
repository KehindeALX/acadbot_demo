"""
URL configuration for AcadBot project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
# from drf_spectacular.views import (
#     SpectacularAPIView,
#     SpectacularSwaggerView,
#     SpectacularRedocView,
# )

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API Schema & Documentation (disabled - requires drf_spectacular)
    # path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # API Endpoints
    path('api/auth/', include('apps.accounts.urls')),
    path('api/careers/', include('apps.careers.urls')),
    path('api/courses/', include('apps.courses.urls')),
    path('api/matching/', include('apps.matching.urls')),
    path('api/sessions/', include('apps.sessions.urls')),
    path('api/progress/', include('apps.progress.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Debug toolbar URLs
    # import debug_toolbar
    # urlpatterns = [path('__debug__/', include(debug_toolbar.urls))] + urlpatterns
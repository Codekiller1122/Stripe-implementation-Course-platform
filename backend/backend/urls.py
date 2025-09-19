from django.contrib import admin
from django.urls import path, include
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('courses.urls')),
    path('webhooks/stripe/', include('courses.webhook_urls')),
]

# myproject/urls.py

from django.contrib import admin
from django.urls import path, include # Ensure 'include' is imported

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')), # Add Django's built-in auth URLs
    path('', include('dashboard_app.urls')),
]

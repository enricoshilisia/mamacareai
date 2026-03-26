"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.conf import settings as django_settings

urlpatterns = [
    path('admin/', admin.site.urls),

    # Silence browser auto-requests
    path('service-worker.js', lambda _: HttpResponse(
        open(django_settings.BASE_DIR / 'static/sw.js').read(),
        content_type='application/javascript'
    )),
    path('.well-known/appspecific/com.chrome.devtools.json', lambda _: HttpResponse('{}', content_type='application/json')),


    # MamaCare apps
    path('', include('mothers.urls', namespace='mothers')),

    # Future apps — uncomment as you build them
    # path('reminders/', include('reminders.urls', namespace='reminders')),
    path("chat/", include("chat.urls", namespace="chat")),
    path("cry/", include("predictions.urls", namespace="predictions")),
    path("doctors/", include("physicians.urls", namespace="physicians")),
    path("consultations/", include("consultations.urls", namespace="consultations")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
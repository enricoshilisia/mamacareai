from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("subscribe/",          views.subscribe,          name="subscribe"),
    path("unsubscribe/",        views.unsubscribe,        name="unsubscribe"),
    path("notifications/",      views.list_notifications, name="list"),
    path("notifications/read/", views.mark_all_read,      name="mark_read"),
]

from django.urls import path
from . import views

app_name = "consultations"

urlpatterns = [
    path("assess/<uuid:conv_id>/",   views.assess,                name="assess"),
    path("doctors/",                 views.doctors_list,          name="doctors_list"),
    path("assess-cry/",              views.assess_cry,            name="assess_cry"),
    path("request/",                 views.request_consultation,  name="request"),
    path("<uuid:pk>/waiting/",       views.waiting,               name="waiting"),
    path("<uuid:pk>/chat/",          views.chat_room,             name="chat_room"),
    path("<uuid:pk>/message/",       views.send_message,          name="send_message"),
    path("<uuid:pk>/poll/",          views.poll_messages,         name="poll"),
    path("inbox/",                   views.inbox,                 name="inbox"),
    path("<uuid:pk>/respond/",       views.respond,               name="respond"),
    path("<uuid:pk>/complete/",      views.complete,              name="complete"),
    path("pending-count/",           views.pending_count,         name="pending_count"),
]

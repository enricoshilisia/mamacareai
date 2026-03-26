from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("",                            views.chat_home,          name="chat_home"),
    path("child/<uuid:child_pk>/",      views.start_with_child,   name="start_with_child"),
    path("<uuid:conv_id>/",             views.chat_room,          name="chat_room"),
    path("<uuid:conv_id>/stream/",      views.stream_reply,       name="stream_reply"),
    path("<uuid:conv_id>/new/",         views.new_conversation,   name="new_conversation"),
    path("history/",                    views.conversation_list,  name="conversation_list"),
]
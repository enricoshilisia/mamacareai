from django.urls import path
from . import views

app_name = "physicians"

urlpatterns = [
    path("home/",                   views.physician_home,        name="physician_home"),
    path("",                        views.physician_list,        name="physician_list"),
    path("<uuid:pk>/",              views.physician_detail,      name="physician_detail"),
    path("register/",               views.physician_register_step1, name="physician_register"),
    path("register/step2/",         views.physician_register_step2, name="physician_register_step2"),
    path("register/step3/",         views.physician_register_step3, name="physician_register_step3"),
    path("register/success/",       views.registration_success,  name="registration_success"),
    path("recommend/",              views.recommend_doctors,     name="recommend_doctors"),
]
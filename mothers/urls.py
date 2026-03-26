from django.urls import path
from . import views

app_name = "mothers"

urlpatterns = [
    # Auth
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Registration (step-wise)
    path("register/", views.register_step1, name="register_step1"),
    path("register/step2/", views.register_step2, name="register_step2"),
    path("register/step3/", views.register_step3, name="register_step3"),

    # Main
    path("", views.home, name="home"),
    path("profile/", views.profile, name="profile"),

    # Children
    path("child/add/", views.add_child, name="add_child"),
    path("child/<uuid:pk>/", views.child_detail, name="child_detail"),
    path("child/<uuid:pk>/edit/", views.edit_child, name="edit_child"),
]
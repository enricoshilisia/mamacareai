from django.urls import path
from . import views

app_name = "predictions"

urlpatterns = [
    path("",           views.cry_analyser, name="cry_analyser"),
    path("history/",   views.cry_history,  name="cry_history"),   # ← moved up
    path("<uuid:pk>/", views.cry_result,   name="cry_result"),
    path("ajax/",      views.cry_analyse_ajax,   name="cry_analyse_ajax"),
]
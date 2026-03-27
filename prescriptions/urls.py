from django.urls import path
from . import views

app_name = 'prescriptions'

urlpatterns = [
    path('<uuid:pk>/suggest/',  views.suggest_drugs,        name='suggest'),
    path('<uuid:pk>/confirm/',  views.confirm_prescription,  name='confirm'),
    path('<uuid:pk>/get/',      views.get_prescription,      name='get'),
]

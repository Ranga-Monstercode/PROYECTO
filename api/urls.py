from django.urls import path
from .views import registrar_cliente, login_cliente

urlpatterns = [
    path('registrar/', registrar_cliente, name='registrar'),
    path('login/', login_cliente, name='login'),
]

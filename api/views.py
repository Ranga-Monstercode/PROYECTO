from django.shortcuts import render

# Create your views here.

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from .models import Cliente
from .serializers import ClienteSerializer

# Registro de cliente
@api_view(['POST'])
def registrar_cliente(request):
    serializer = ClienteSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"mensaje": "Cliente registrado con éxito"}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Login con RUT y contraseña
@api_view(['POST'])
def login_cliente(request):
    rut = request.data.get("rut")
    password = request.data.get("password")

    try:
        cliente = Cliente.objects.get(rut=rut)
        if cliente.verificar_password(password):
            return Response({"mensaje": "Login exitoso", "cliente": cliente.nombre}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Contraseña incorrecta"}, status=status.HTTP_401_UNAUTHORIZED)
    except Cliente.DoesNotExist:
        return Response({"error": "Cliente no encontrado"}, status=status.HTTP_404_NOT_FOUND)

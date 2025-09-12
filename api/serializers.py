from rest_framework import serializers
from .models import Cliente

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nombre', 'telefono', 'rut', 'correo', 'password']
        extra_kwargs = {'password': {'write_only': True}}

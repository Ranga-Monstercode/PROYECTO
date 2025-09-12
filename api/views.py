from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Cliente
from .serializers import ClienteSerializer
from rest_framework_simplejwt.tokens import RefreshToken

# Registro de cliente - Permitir acceso sin autenticación
@api_view(['POST'])
@permission_classes([AllowAny])  # ✅ Esto permite acceso sin token
def registrar_cliente(request):
    try:
        serializer = ClienteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "mensaje": "Cliente registrado con éxito",
                "user": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "error": "Datos inválidos",
            "detalles": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({
            "error": "Error interno del servidor",
            "detalles": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Login con RUT y contraseña - También permitir acceso sin autenticación
@api_view(['POST'])
@permission_classes([AllowAny])  # ✅ Esto permite acceso sin token
def login_cliente(request):
    try:
        rut = request.data.get("rut")
        password = request.data.get("password")

        if not rut or not password:
            return Response({
                "error": "RUT y contraseña son requeridos"
            }, status=status.HTTP_400_BAD_REQUEST)

        cliente = Cliente.objects.get(rut=rut)
        if cliente.verificar_password(password):
            # Serializar datos del cliente
            serializer = ClienteSerializer(cliente)
            
            # Generar tokens JWT
            refresh = RefreshToken.for_user(cliente)
            
            return Response({
                "mensaje": "Login exitoso", 
                "user": serializer.data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh)
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "error": "Contraseña incorrecta"
            }, status=status.HTTP_401_UNAUTHORIZED)
            
    except Cliente.DoesNotExist:
        return Response({
            "error": "Cliente no encontrado"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "error": "Error interno del servidor",
            "detalles": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
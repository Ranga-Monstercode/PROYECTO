from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status, viewsets
from .models import Usuario, Paciente, Administrador, Medico, Agenda, Cita, Notificacion, Horario
from .serializers import UsuarioSerializer, PacienteSerializer, AdministradorSerializer, MedicoSerializer, AgendaSerializer, CitaSerializer, NotificacionSerializer, HorarioSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password, check_password

# Registro de paciente (cliente)
@api_view(['POST'])
@permission_classes([AllowAny])
def registrar_cliente(request):
    try:
        data = request.data.copy()
        # Hashea la contraseña antes de pasarla al serializer
        if 'usuario' in data and 'password' in data['usuario']:
            data['usuario']['password'] = make_password(data['usuario']['password'])
        serializer = PacienteSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "mensaje": "Paciente registrado con éxito",
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

# Login con RUT y contraseña
@api_view(['POST'])
@permission_classes([AllowAny])
def login_cliente(request):
    try:
        rut = request.data.get("rut")
        password = request.data.get("password")

        if not rut or not password:
            return Response({
                "error": "RUT y contraseña son requeridos"
            }, status=status.HTTP_400_BAD_REQUEST)

        paciente = Paciente.objects.get(usuario__rut=rut)
        # Verificar contraseña usando hash
        if check_password(password, paciente.usuario.password):
            serializer = PacienteSerializer(paciente)
            refresh = RefreshToken.for_user(paciente.usuario)
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
    except Paciente.DoesNotExist:
        return Response({
            "error": "Paciente no encontrado"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            "error": "Error interno del servidor",
            "detalles": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_medico_admin(request):
    rut = request.data.get("rut")
    password = request.data.get("password")
    if not rut or not password:
        return Response({"error": "RUT y contraseña son requeridos"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        usuario = Usuario.objects.get(rut=rut)
        if usuario.rol not in ['Medico', 'Administrador']:
            return Response({"error": "Solo médicos o administradores pueden iniciar sesión aquí."}, status=status.HTTP_403_FORBIDDEN)
        # Verificar contraseña usando hash
        if check_password(password, usuario.password):
            serializer = UsuarioSerializer(usuario)
            refresh = RefreshToken.for_user(usuario)
            return Response({
                "mensaje": "Login exitoso",
                "user": serializer.data,
                "token": str(refresh.access_token),
                "refresh_token": str(refresh)
            }, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Contraseña incorrecta"}, status=status.HTTP_401_UNAUTHORIZED)
    except Usuario.DoesNotExist:
        return Response({"error": "Usuario no encontrado"}, status=status.HTTP_404_NOT_FOUND)

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer

class PacienteViewSet(viewsets.ModelViewSet):
    queryset = Paciente.objects.all()
    serializer_class = PacienteSerializer
    permission_classes = [AllowAny]

class AdministradorViewSet(viewsets.ModelViewSet):
    queryset = Administrador.objects.all()
    serializer_class = AdministradorSerializer
    permission_classes = [AllowAny]

class MedicoViewSet(viewsets.ModelViewSet):
    queryset = Medico.objects.all()
    serializer_class = MedicoSerializer
    permission_classes = [AllowAny]

class AgendaViewSet(viewsets.ModelViewSet):
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer
    permission_classes = [AllowAny]

class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all()
    serializer_class = CitaSerializer
    permission_classes = [AllowAny]

class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer
    permission_classes = [AllowAny]

class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer
    permission_classes = [AllowAny]
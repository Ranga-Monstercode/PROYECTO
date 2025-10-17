from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import get_object_or_404
from .models import (
    Usuario, Paciente, Administrador, Medico, 
    Agenda, Cita, Notificacion, Horario, Especialidad, MedicoEspecialidad
)
from .serializers import (
    UsuarioSerializer, PacienteSerializer, AdministradorSerializer,
    MedicoSerializer, AgendaSerializer, CitaSerializer,
    NotificacionSerializer, HorarioSerializer, EspecialidadSerializer, MedicoEspecialidadSerializer
)

@api_view(['POST'])
@permission_classes([AllowAny])
def registrar_cliente(request):
    try:
        # recibimos datos tal cual vienen del frontend
        serializer = PacienteSerializer(data=request.data)
        if serializer.is_valid():
            paciente = serializer.save()
            return Response({
                "mensaje": "Paciente registrado con éxito",
                "user": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "error": "Datos inválidos",
            "detalles": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        # Añadir logging para depuración
        import traceback, sys
        traceback.print_exc(file=sys.stdout)
        return Response({
            "error": "Error interno del servidor",
            "detalles": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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

@api_view(['POST'])
@permission_classes([AllowAny])
def verificar_rut(request):
    """
    Verifica si un RUT existe en el sistema y devuelve los datos del usuario
    """
    rut = request.data.get('rut')
    
    if not rut:
        return Response(
            {'error': 'El RUT es requerido'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        usuario = Usuario.objects.get(rut=rut)
        serializer = UsuarioSerializer(usuario)
        return Response(serializer.data)
    except Usuario.DoesNotExist:
        return Response(
            {'error': 'RUT no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer
    permission_classes = [AllowAny]

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
    
    @action(detail=True, methods=['post'])
    def asignar_especialidad(self, request, pk=None):
        """
        Asigna o actualiza la especialidad de un médico
        """
        medico = self.get_object()
        especialidad = request.data.get('especialidad')
        
        if not especialidad:
            return Response(
                {'error': 'La especialidad es requerida'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        medico.especialidad = especialidad
        medico.save()
        
        serializer = self.get_serializer(medico)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def horarios(self, request, pk=None):
        """
        Obtiene los horarios de un médico específico
        """
        medico = self.get_object()
        horarios = Horario.objects.filter(medico=medico)
        serializer = HorarioSerializer(horarios, many=True)
        return Response(serializer.data)

class MedicoEspecialidadViewSet(viewsets.ModelViewSet):
    queryset = MedicoEspecialidad.objects.all()
    serializer_class = MedicoEspecialidadSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        medico_id = self.request.query_params.get('medico', None)
        if medico_id:
            qs = qs.filter(medico__usuario__id=medico_id)  # buscar por id de usuario o medico
        return qs

class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        medico_esp = self.request.query_params.get('medico_especialidad', None)
        if medico_esp:
            qs = qs.filter(medico_especialidad__id=medico_esp)
        return qs

class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all()
    serializer_class = CitaSerializer
    permission_classes = [AllowAny]

class AgendaViewSet(viewsets.ModelViewSet):
    queryset = Agenda.objects.all()
    serializer_class = AgendaSerializer
    permission_classes = [AllowAny]

class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer
    permission_classes = [AllowAny]

class EspecialidadViewSet(viewsets.ModelViewSet):
    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer
    permission_classes = [AllowAny]

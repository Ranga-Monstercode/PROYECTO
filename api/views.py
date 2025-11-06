from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password, check_password 
from django.utils import timezone
from datetime import datetime, timedelta
import pytz
from rest_framework_simplejwt.tokens import RefreshToken  
from django.core.mail import EmailMessage  
import qrcode  
import io 

from .models import (
    Usuario, Paciente, Administrador, Medico, MedicoEspecialidad,
    Cita, Notificacion, Horario, Especialidad, Box
)
from .serializers import (
    UsuarioSerializer, PacienteSerializer, AdministradorSerializer,
    MedicoSerializer, MedicoEspecialidadSerializer,
    CitaSerializer, NotificacionSerializer, HorarioSerializer,
    EspecialidadSerializer, BoxSerializer
)

@api_view(['POST'])
@permission_classes([AllowAny])
def verificar_o_crear_rut(request):
    """
    Verifica si un RUT existe. Si no existe, crea un usuario temporal.
    """
    rut = request.data.get('rut')
    
    if not rut:
        return Response(
            {'error': 'El RUT es requerido'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        #  Buscar usuario existente
        usuario = Usuario.objects.get(rut=rut)
        
        #  Obtener o crear paciente
        try:
            paciente = Paciente.objects.get(usuario=usuario)
        except Paciente.DoesNotExist:
            paciente = Paciente.objects.create(usuario=usuario)
        
        #  Verificar si tiene datos completos
        es_temporal = usuario.correo.endswith('@temporal.com')
        
        serializer = UsuarioSerializer(usuario)
        return Response({
            'existe': True,
            'usuario': serializer.data,
            'paciente_id': paciente.pk,  #  Siempre devolver paciente_id
            'es_temporal': es_temporal,
            'mensaje': 'Usuario encontrado' if not es_temporal else 'Usuario temporal encontrado'
        })
    except Usuario.DoesNotExist:
        #  Crear usuario temporal
        try:
            nuevo_usuario = Usuario.objects.create(
                rut=rut,
                nombre=f"Usuario {rut}",
                correo=f"{rut}@temporal.com",
                password=make_password(rut),
                rol='Paciente'
            )
            
            #  Crear paciente asociado
            paciente = Paciente.objects.create(usuario=nuevo_usuario)
            
            serializer = UsuarioSerializer(nuevo_usuario)
            return Response({
                'existe': False,
                'usuario': serializer.data,
                'es_temporal': True,
                'paciente_id': paciente.pk,  #  Devolver paciente_id
                'mensaje': 'Usuario temporal creado exitosamente'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Error al crear usuario temporal: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['POST'])
@permission_classes([AllowAny])
def registrar_cliente(request):
    try:
        rut = request.data.get('usuario', {}).get('rut')
        
        if not rut:
            return Response({
                "error": "El RUT es requerido"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        #  Verificar si ya existe un usuario con ese RUT
        try:
            usuario_existente = Usuario.objects.get(rut=rut)
            
            # Verificar si tiene citas previas
            tiene_citas = Cita.objects.filter(usuario=usuario_existente).exists()
            
            if tiene_citas:
                return Response({
                    "error": "rut_con_historial",
                    "mensaje": "Este RUT ya tiene historial de citas en el sistema",
                    "usuario_id": usuario_existente.id,
                    "tiene_citas": True
                }, status=status.HTTP_409_CONFLICT)
            else:
                # Si no tiene citas, simplemente actualizar los datos
                return actualizar_usuario_existente(usuario_existente, request.data)
        except Usuario.DoesNotExist:
            #  No existe, crear nuevo
            pass
        
        # Crear nuevo usuario y paciente
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
        import traceback, sys
        traceback.print_exc(file=sys.stdout)
        return Response({
            "error": "Error interno del servidor",
            "detalles": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def actualizar_usuario_con_historial(request):
    """
    Actualiza un usuario temporal que tiene historial de citas
    """
    try:
        usuario_id = request.data.get('usuario_id')
        usuario_data = request.data.get('usuario', {})
        
        if not usuario_id:
            return Response({
                "error": "usuario_id es requerido"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        usuario = Usuario.objects.get(id=usuario_id)
        
        #  Actualizar datos del usuario
        usuario.nombre = usuario_data.get('nombre', usuario.nombre)
        usuario.correo = usuario_data.get('correo', usuario.correo)
        usuario.telefono = usuario_data.get('telefono', usuario.telefono)
        
        if usuario_data.get('password'):
            usuario.password = make_password(usuario_data['password'])
        
        usuario.save()
        
        #  Actualizar datos del paciente si existe
        try:
            paciente = Paciente.objects.get(usuario=usuario)
            if 'direccion' in request.data:
                paciente.direccion = request.data['direccion']
                paciente.save()
        except Paciente.DoesNotExist:
            #  Crear paciente si no existe
            paciente = Paciente.objects.create(
                usuario=usuario,
                direccion=request.data.get('direccion', '')
            )
        
        serializer = PacienteSerializer(paciente)
        return Response({
            "mensaje": "Usuario actualizado exitosamente",
            "user": serializer.data
        }, status=status.HTTP_200_OK)
    except Usuario.DoesNotExist:
        return Response({
            "error": "Usuario no encontrado"
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "error": "Error al actualizar usuario",
            "detalles": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def actualizar_usuario_existente(usuario, data):
    """Helper para actualizar usuario existente"""
    try:
        usuario_data = data.get('usuario', {})
        
        usuario.nombre = usuario_data.get('nombre', usuario.nombre)
        usuario.correo = usuario_data.get('correo', usuario.correo)
        usuario.telefono = usuario_data.get('telefono', usuario.telefono)
        
        if usuario_data.get('password'):
            usuario.password = make_password(usuario_data['password'])
        
        usuario.save()
        
        # Actualizar paciente
        try:
            paciente = Paciente.objects.get(usuario=usuario)
            if 'direccion' in data:
                paciente.direccion = data['direccion']
                paciente.save()
        except Paciente.DoesNotExist:
            paciente = Paciente.objects.create(
                usuario=usuario,
                direccion=data.get('direccion', '')
            )
        
        serializer = PacienteSerializer(paciente)
        return Response({
            "mensaje": "Usuario actualizado exitosamente",
            "user": serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "error": "Error al actualizar usuario",
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

class EspecialidadViewSet(viewsets.ModelViewSet):
    queryset = Especialidad.objects.all()
    serializer_class = EspecialidadSerializer
    permission_classes = [AllowAny]

class BoxViewSet(viewsets.ModelViewSet):
    queryset = Box.objects.all()
    serializer_class = BoxSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        medico_id = self.request.query_params.get('medico')
        if medico_id:
            qs = qs.filter(medico_id=medico_id)
        return qs

class MedicoEspecialidadViewSet(viewsets.ModelViewSet):
    queryset = MedicoEspecialidad.objects.all()
    serializer_class = MedicoEspecialidadSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        medico_id = self.request.query_params.get('medico')
        if medico_id:
            qs = qs.filter(medico_id=medico_id)
        return qs

class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        me_id = self.request.query_params.get('medico_especialidad')
        if me_id:
            qs = qs.filter(medico_especialidad_id=me_id)
        return qs

class CitaViewSet(viewsets.ModelViewSet):
    queryset = Cita.objects.all()
    serializer_class = CitaSerializer
    
    def _send_appointment_email(self, cita, subject, body, attach_qr=False):
        """
        Envía un correo al paciente de la cita. Opcionalmente adjunta un QR con el ID de la cita.
        Usa DEFAULT_FROM_EMAIL configurado en settings.py.
        """
        try:
            paciente_email = cita.usuario.correo
            email = EmailMessage(subject, body, None, [paciente_email])

            if attach_qr:
                qr_data = str(cita.id)
                qr_img = qrcode.make(qr_data)
                buffer = io.BytesIO()
                qr_img.save(buffer, format='PNG')
                buffer.seek(0)
                email.attach(f'cita_qr_{cita.id}.png', buffer.read(), 'image/png')

            email.send(fail_silently=False)
            print(f"✅ Correo enviado a {paciente_email} para la cita {cita.id}")
        except Exception as e:
            print(f"❌ Error al enviar correo para la cita {cita.id}: {str(e)}")

    def perform_create(self, serializer):
        """
        Enviar correo al crear una cita: 'Hora Agendada - Pendiente de Aceptación'
        """
        cita = serializer.save()
        asunto = "Hora Agendada - Pendiente de Aceptación"
        cuerpo = (
            f"Estimado/a {cita.usuario.nombre},\n\n"
            f"Su cita ha sido agendada para el {cita.fechaHora.strftime('%d-%m-%Y a las %H:%M')} "
            f"con el Dr(a). {cita.medico.usuario.nombre}.\n\n"
            "Su cita está pendiente de confirmación por parte de nuestro personal. "
            "Recibirá otro correo una vez que sea aceptada.\n\n"
            "Gracias por preferirnos."
        )
        self._send_appointment_email(cita, asunto, cuerpo)

    def update(self, request, *args, **kwargs):
        """
        Actualización completa (PUT) + email si cambia a Confirmada
        """
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            old_estado = instance.estado  # <- agregado

            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            updated_instance = serializer.instance  # <- agregado
            if old_estado != 'Confirmada' and updated_instance.estado == 'Confirmada':
                asunto = "¡Tu Cita ha sido Confirmada!"
                cuerpo = (
                    f"Estimado/a {updated_instance.usuario.nombre},\n\n"
                    f"Nos complace informarle que su cita para el "
                    f"{updated_instance.fechaHora.strftime('%d-%m-%Y a las %H:%M')} "
                    f"con el Dr(a). {updated_instance.medico.usuario.nombre} ha sido confirmada.\n\n"
                    "Adjuntamos un código QR que puede presentar en recepción. ¡Le esperamos!\n\n"
                    "Gracias por su confianza."
                )
                self._send_appointment_email(updated_instance, asunto, cuerpo, attach_qr=True)

            return Response(serializer.data)
        except Exception as e:
            print(f" Error actualizando cita: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'detail': f'Error actualizando cita: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def partial_update(self, request, *args, **kwargs):
        """
        Actualización parcial (PATCH) - delega en update
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['patch'], url_path='actualizar-estado')
    def actualizar_estado(self, request, pk=None):
        """
        Actualiza estado/prioridad/descripcion; si estado cambia a Confirmada, envía email con QR
        """
        try:
            cita = self.get_object()
            old_estado = cita.estado  # <- agregado

            if 'estado' in request.data:
                cita.estado = request.data['estado']
            if 'prioridad' in request.data:
                cita.prioridad = request.data['prioridad']
            if 'descripcion' in request.data:
                cita.descripcion = request.data['descripcion']

            cita.save()

            if old_estado != 'Confirmada' and cita.estado == 'Confirmada':
                asunto = "¡Tu Cita ha sido Confirmada!"
                cuerpo = (
                    f"Estimado/a {cita.usuario.nombre},\n\n"
                    f"Nos complace informarle que su cita para el "
                    f"{cita.fechaHora.strftime('%d-%m-%Y a las %H:%M')} "
                    f"con el Dr(a). {cita.medico.usuario.nombre} ha sido confirmada.\n\n"
                    "Adjuntamos un código QR que puede presentar en recepción. ¡Le esperamos!\n\n"
                    "Gracias por su confianza."
                )
                self._send_appointment_email(cita, asunto, cuerpo, attach_qr=True)

            serializer = self.get_serializer(cita)
            return Response(serializer.data)
        except Exception as e:
            print(f" Error actualizando estado de cita: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'detail': f'Error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'], url_path='reprogramar')
    def reprogramar(self, request, pk=None):
        """
        Endpoint para reprogramar una cita (cambiar fecha/hora y marcar como Reprogramada)
        """
        try:
            cita = self.get_object()
            
            # Validar que la cita pueda ser reprogramada
            if cita.estado == 'Cancelada':
                return Response(
                    {'detail': 'No se puede reprogramar una cita cancelada'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            nueva_fecha_hora = request.data.get('fechaHora')
            if not nueva_fecha_hora:
                return Response(
                    {'detail': 'La nueva fecha y hora son requeridas'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Parsear la nueva fecha
            try:
                from datetime import datetime
                if isinstance(nueva_fecha_hora, str):
                    nueva_fecha = datetime.fromisoformat(nueva_fecha_hora.replace('Z', '+00:00'))
                else:
                    nueva_fecha = nueva_fecha_hora
            except (ValueError, AttributeError) as e:
                return Response(
                    {'detail': f'Formato de fecha inválido: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar que la nueva fecha sea futura
            from django.utils import timezone
            if nueva_fecha <= timezone.now():
                return Response(
                    {'detail': 'La nueva fecha debe ser futura'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar intervalo de 15 minutos
            if nueva_fecha.minute not in [0, 15, 30, 45]:
                return Response(
                    {'detail': 'La hora debe ser en intervalos de 15 minutos'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar rango horario (8:00 - 20:00)
            import pytz
            chile_tz = pytz.timezone('America/Santiago')
            if timezone.is_naive(nueva_fecha):
                nueva_fecha = timezone.make_aware(nueva_fecha, timezone.utc)
            fecha_chile = nueva_fecha.astimezone(chile_tz)
            
            if fecha_chile.hour < 8 or fecha_chile.hour >= 20:
                return Response(
                    {'detail': 'La cita debe estar entre 8:00 AM y 8:00 PM'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar que el médico tenga horario configurado
            dias = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']
            dia_nombre = dias[fecha_chile.weekday()]
            hora_chile = fecha_chile.time()
            
            horario_disponible = Horario.objects.filter(
                medico_especialidad=cita.medico_especialidad,
                dia=dia_nombre,
                horaInicio__lte=hora_chile,
                horaFin__gt=hora_chile
            ).exists()
            
            if not horario_disponible:
                return Response(
                    {'detail': f'El médico no tiene disponibilidad configurada para {dia_nombre} a las {hora_chile.strftime("%H:%M")}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar que no haya conflicto con otras citas
            conflictos = Cita.objects.filter(
                medico=cita.medico,
                fechaHora=nueva_fecha,
                estado__in=['Pendiente', 'Confirmada', 'Reprogramada']
            ).exclude(pk=cita.pk)
            
            if conflictos.exists():
                return Response(
                    {'detail': 'Ya existe una cita en este horario para el médico'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar conflicto en mismo box
            h = Horario.objects.filter(
                medico_especialidad=cita.medico_especialidad,
                dia=dia_nombre,
                horaInicio__lte=hora_chile,
                horaFin__gt=hora_chile
            ).select_related('box').first()
            
            if h and h.box_id:
                otras_citas = Cita.objects.filter(
                    medico=cita.medico,
                    fechaHora=nueva_fecha,
                    estado__in=['Pendiente', 'Confirmada', 'Reprogramada']
                ).exclude(pk=cita.pk)
                
                for otra in otras_citas:
                    otra_fecha_chile = otra.fechaHora.astimezone(chile_tz)
                    dia2 = dias[otra_fecha_chile.weekday()]
                    hora2 = otra_fecha_chile.time()
                    h2 = Horario.objects.filter(
                        medico_especialidad=otra.medico_especialidad,
                        dia=dia2,
                        horaInicio__lte=hora2,
                        horaFin__gt=hora2
                    ).first()
                    if h2 and h2.box_id == h.box_id:
                        return Response(
                            {'detail': 'Ya existe una cita en este box a esta hora'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
            # Actualizar la cita
            cita.fechaHora = nueva_fecha
            cita.estado = 'Reprogramada'
            cita.save(skip_validation=True)
            
            serializer = self.get_serializer(cita)
            return Response({
                'detail': 'Cita reprogramada exitosamente',
                'cita': serializer.data
            })
            
        except Exception as e:
            print(f" Error reprogramando cita: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'detail': f'Error reprogramando cita: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def horarios_disponibles(self, request):
        """
        Devuelve slots de 15 minutos disponibles para un médico-especialidad en una fecha dada
        Las citas duran 30 minutos, por lo que se generan slots cada 15 min para mayor flexibilidad
        """
        import pytz
        from datetime import datetime, time, timedelta
        from django.utils import timezone as django_tz
        
        medico_id = request.data.get('medico_id')
        medico_especialidad_id = request.data.get('medico_especialidad_id')
        fecha_str = request.data.get('fecha')
        
        if not all([medico_id, medico_especialidad_id, fecha_str]):
            return Response({"error": "Faltan parámetros"}, status=400)
        
        try:
            medico = Medico.objects.get(pk=medico_id)
            me = MedicoEspecialidad.objects.get(pk=medico_especialidad_id)
            
            if me.medico_id != medico.pk:
                combinaciones = MedicoEspecialidad.objects.filter(medico_id=medico_id).values_list('id', 'especialidad__nombre')
                return Response({
                    "error": "Combinación médico-especialidad no válida",
                    "medico_id": medico_id,
                    "medico_especialidad_id": medico_especialidad_id,
                    "combinaciones_validas": list(combinaciones)
                }, status=400)
            
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            dias = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']
            dia_nombre = dias[fecha.weekday()]
            
            horarios = Horario.objects.filter(medico_especialidad=me, dia=dia_nombre).select_related('box')
            
            if not horarios.exists():
                return Response({
                    "disponibles": [],
                    "mensaje": "No hay horarios configurados para este día"
                })
            
            #  Usar timezone de Chile
            chile_tz = pytz.timezone('America/Santiago')
            
            #  Calcular rango de fecha en UTC para la consulta
            inicio_dia_chile = chile_tz.localize(datetime.combine(fecha, time.min))
            fin_dia_chile = chile_tz.localize(datetime.combine(fecha, time.max))
            
            inicio_dia_utc = inicio_dia_chile.astimezone(pytz.UTC)
            fin_dia_utc = fin_dia_chile.astimezone(pytz.UTC)
            
            print(f"🔍 Buscando citas entre {inicio_dia_utc} y {fin_dia_utc}")
            
            #  PRIMERO: Obtener todas las citas ocupadas en UTC
            citas = Cita.objects.filter(
                medico=medico,
                fechaHora__gte=inicio_dia_utc,
                fechaHora__lte=fin_dia_utc,
                estado__in=['Pendiente', 'Confirmada']
            )
            
            print(f"📋 Citas encontradas: {citas.count()}")
            
            #  Crear set de rangos ocupados (inicio y fin de cada cita)
            rangos_ocupados = []
            for c in citas:
                fecha_utc = c.fechaHora
                if django_tz.is_naive(fecha_utc):
                    fecha_utc = django_tz.make_aware(fecha_utc, pytz.UTC)
                
                # Cada cita dura 30 minutos
                inicio_cita = fecha_utc
                fin_cita = fecha_utc + timedelta(minutes=30)
                
                rangos_ocupados.append({
                    'inicio': inicio_cita,
                    'fin': fin_cita
                })
                
                # Convertir a Chile para logging
                fecha_chile = fecha_utc.astimezone(chile_tz)
                fin_chile = fin_cita.astimezone(chile_tz)
                print(f"⏰ Cita ocupada - Chile: {fecha_chile.strftime('%H:%M')} a {fin_chile.strftime('%H:%M')}")
            
            print(f"🚫 Total rangos ocupados: {len(rangos_ocupados)}")
            
            #  SEGUNDO: Generar todos los slots posibles en UTC (cada 15 min)
            slots_totales = []
            for h in horarios:
                inicio = h.horaInicio
                fin = h.horaFin
                box_nombre = h.box.nombre if h.box else "Sin box"
                
                actual = datetime.combine(fecha, inicio)
                fin_dt = datetime.combine(fecha, fin)
                
                while actual < fin_dt:
                    # Verificar que haya espacio para una cita completa (30 min)
                    if (actual + timedelta(minutes=30)) <= fin_dt:
                        # Crear datetime con timezone de Chile
                        dt_chile = chile_tz.localize(actual)
                        dt_utc = dt_chile.astimezone(pytz.UTC)
                        
                        # Calcular fin del slot (30 min después)
                        fin_slot_chile = chile_tz.localize(actual + timedelta(minutes=30))
                        fin_slot_utc = fin_slot_chile.astimezone(pytz.UTC)
                        
                        slots_totales.append({
                            'horaInicio': actual.time().strftime('%H:%M'),
                            'horaFin': (actual + timedelta(minutes=30)).strftime('%H:%M'),
                            'box': box_nombre,
                            'fechaHora': dt_utc.isoformat(),
                            'inicio_utc': dt_utc,
                            'fin_utc': fin_slot_utc
                        })
                    
                    # Avanzar de 15 en 15 min para generar todos los slots posibles
                    actual += timedelta(minutes=15)
            
            print(f"📊 Total slots generados: {len(slots_totales)}")
            
            #  TERCERO: Filtrar slots que NO se solapen con citas existentes
            def hay_solapamiento(slot_inicio, slot_fin, rangos):
                """
                Verifica si un slot se solapa con algún rango ocupado
                Hay solapamiento si:
                - El inicio del slot está dentro de una cita: slot_inicio < rango_fin AND slot_inicio >= rango_inicio
                - El fin del slot está dentro de una cita: slot_fin > rango_inicio AND slot_fin <= rango_fin
                - El slot envuelve completamente una cita: slot_inicio <= rango_inicio AND slot_fin >= rango_fin
                """
                for rango in rangos:
                    # Normalizar para comparación
                    if (slot_inicio < rango['fin'] and slot_fin > rango['inicio']):
                        return True
                return False
            
            slots_disponibles = []
            for slot in slots_totales:
                if not hay_solapamiento(slot['inicio_utc'], slot['fin_utc'], rangos_ocupados):
                    # Remover campos internos antes de devolver
                    slot_limpio = {
                        'horaInicio': slot['horaInicio'],
                        'horaFin': slot['horaFin'],
                        'box': slot['box'],
                        'fechaHora': slot['fechaHora']
                    }
                    slots_disponibles.append(slot_limpio)
                else:
                    print(f"⛔ Descartando slot: {slot['horaInicio']}-{slot['horaFin']} (solapamiento detectado)")
            
            print(f" Slots disponibles finales: {len(slots_disponibles)}")
            
            return Response({
                "disponibles": slots_disponibles,
                "mensaje": f"Se encontraron {len(slots_disponibles)} horarios disponibles"
            })
            
        except Medico.DoesNotExist:
            return Response({"error": "Médico no encontrado"}, status=404)
        except MedicoEspecialidad.DoesNotExist:
            return Response({"error": "Relación médico-especialidad no encontrada"}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)

    @action(detail=False, methods=['post'])
    def validar_horario(self, request):
        """
        Valida si un horario específico está disponible antes de crear la cita.
        """
        medico_id = request.data.get('medico_id')
        fecha_hora_str = request.data.get('fechaHora')

        if not all([medico_id, fecha_hora_str]):
            return Response(
                {"error": "medico_id y fechaHora son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            fecha_hora = datetime.fromisoformat(fecha_hora_str.replace('Z', '+00:00'))
            medico = Medico.objects.get(pk=medico_id)
        except (ValueError, Medico.DoesNotExist):
            return Response(
                {"error": "Datos inválidos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validaciones
        errores = []

        # Intervalo de 15 minutos
        if fecha_hora.minute not in [0, 15, 30, 45]:
            errores.append("La hora debe ser en intervalos de 15 minutos")

        # Rango horario
        if fecha_hora.hour < 8 or fecha_hora.hour >= 20:
            errores.append("La cita debe estar entre 8:00 AM y 8:00 PM")

        # Conflicto exacto
        if Cita.objects.filter(
            medico=medico,
            fechaHora=fecha_hora,
            estado__in=['Pendiente', 'Confirmada']
        ).exists():
            errores.append("Ya existe una cita en este horario")

        # Espacio de 1 hora
        hora_inicio = fecha_hora - timedelta(hours=1)
        hora_fin = fecha_hora + timedelta(hours=1)

        if Cita.objects.filter(
            medico=medico,
            fechaHora__gte=hora_inicio,
            fechaHora__lte=hora_fin,
            estado__in=['Pendiente', 'Confirmada']
        ).exists():
            errores.append("Debe haber al menos 1 hora de diferencia con otras citas")

        if errores:
            return Response(
                {"valido": False, "errores": errores},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"valido": True, "mensaje": "Horario disponible"},
            status=status.HTTP_200_OK
        )

class NotificacionViewSet(viewsets.ModelViewSet):
    queryset = Notificacion.objects.all()
    serializer_class = NotificacionSerializer

class MedicoViewSet(viewsets.ModelViewSet):
    queryset = Medico.objects.all()
    serializer_class = MedicoSerializer
    permission_classes = [AllowAny]

    def destroy(self, request, *args, **kwargs):
        """
        Eliminar médico y su usuario asociado
        """
        try:
            instance = self.get_object()
            usuario = instance.usuario
            
            # Eliminar el médico (esto eliminará en cascada por OneToOneField)
            instance.delete()
            
            # Eliminar el usuario asociado
            usuario.delete()
            
            print(f" Médico y usuario eliminados correctamente")
            
            return Response(
                {'message': 'Médico eliminado correctamente'}, 
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            print(f" Error eliminando médico: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {'detail': f'Error eliminando médico: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def horarios(self, request, pk=None):
        """
        Horarios de un médico (todas sus especialidades)
        """
        medico = self.get_object()
        horarios = Horario.objects.filter(medico_especialidad__medico=medico)
        serializer = HorarioSerializer(horarios, many=True)
        return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    rut = request.data.get('rut')
    password = request.data.get('password')
    
    if not rut or not password:
        return Response({'error': 'RUT y contraseña requeridos'}, status=400)
    
    try:
        usuario = Usuario.objects.get(rut=rut)
        
        # Verificar contraseña
        if not check_password(password, usuario.password):
            return Response({'error': 'Contraseña incorrecta'}, status=401)
        
        #  GENERAR TOKEN JWT VÁLIDO
        refresh = RefreshToken.for_user(usuario)
        access_token = str(refresh.access_token)
        
        print(f" Token generado para {usuario.nombre}: {access_token[:30]}...")
        
        # Devolver respuesta
        return Response({
            'user': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'correo': usuario.correo,
                'rut': usuario.rut,
                'telefono': usuario.telefono,
                'rol': usuario.rol
            },
            'token': access_token,  #  Token JWT válido
            'message': f'Bienvenido, {usuario.nombre}'
        })
        
    except Usuario.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        print(f" Error en login: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({'error': 'Error interno del servidor'}, status=500)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import Usuario

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login endpoint que devuelve token JWT
    """
    correo = request.data.get('correo')
    password = request.data.get('password')
    
    if not correo or not password:
        return Response(
            {'detail': 'Correo y contraseña son requeridos'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Buscar usuario por correo
        usuario = Usuario.objects.get(correo=correo)
        
        # Verificar contraseña
        if not usuario.check_password(password):
            return Response(
                {'detail': 'Credenciales inválidas'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generar tokens JWT
        refresh = RefreshToken.for_user(usuario)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        # Preparar datos del usuario
        user_data = {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'correo': usuario.correo,
            'rut': usuario.rut,
            'telefono': usuario.telefono,
            'rol': usuario.rol
        }
        
        # Devolver respuesta con token
        return Response({
            'access': access_token,
            'refresh': refresh_token,
            'user': user_data
        }, status=status.HTTP_200_OK)
        
    except Usuario.DoesNotExist:
        return Response(
            {'detail': 'Credenciales inválidas'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {'detail': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


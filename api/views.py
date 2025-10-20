from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth.hashers import make_password, check_password  # ✅ Agregar check_password
from django.utils import timezone
from datetime import datetime, timedelta
import pytz
from rest_framework_simplejwt.tokens import RefreshToken  # <- agregar

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
    permission_classes = [AllowAny]

    def update(self, request, *args, **kwargs):
        """
        Permite actualizar una cita existente
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """
        Permite actualizar parcialmente una cita
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

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
            
            # ✅ Usar timezone de Chile
            chile_tz = pytz.timezone('America/Santiago')
            
            # ✅ Calcular rango de fecha en UTC para la consulta
            inicio_dia_chile = chile_tz.localize(datetime.combine(fecha, time.min))
            fin_dia_chile = chile_tz.localize(datetime.combine(fecha, time.max))
            
            inicio_dia_utc = inicio_dia_chile.astimezone(pytz.UTC)
            fin_dia_utc = fin_dia_chile.astimezone(pytz.UTC)
            
            print(f"🔍 Buscando citas entre {inicio_dia_utc} y {fin_dia_utc}")
            
            # ✅ PRIMERO: Obtener todas las citas ocupadas en UTC
            citas = Cita.objects.filter(
                medico=medico,
                fechaHora__gte=inicio_dia_utc,
                fechaHora__lte=fin_dia_utc,
                estado__in=['Pendiente', 'Confirmada']
            )
            
            print(f"📋 Citas encontradas: {citas.count()}")
            
            # ✅ Crear set de rangos ocupados (inicio y fin de cada cita)
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
            
            # ✅ SEGUNDO: Generar todos los slots posibles en UTC (cada 15 min)
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
            
            # ✅ TERCERO: Filtrar slots que NO se solapen con citas existentes
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
            
            print(f"✅ Slots disponibles finales: {len(slots_disponibles)}")
            
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
    rut = (request.data.get('rut') or '').strip()     # <- usar tal cual
    password = request.data.get('password') or ''
    
    if not rut or not password:
        return Response({'error': 'RUT y contraseña son requeridos'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # ❌ eliminar normalización; buscar exactamente por el valor recibido
        usuario = Usuario.objects.get(rut=rut)

        if not check_password(password, usuario.password):
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user_data = {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'correo': usuario.correo,
            'rut': usuario.rut,
            'telefono': usuario.telefono,
            'rol': usuario.rol,
        }
        if usuario.rol == 'Paciente':
            paciente, created = Paciente.objects.get_or_create(usuario=usuario)
            user_data['paciente_id'] = paciente.pk
        elif usuario.rol == 'Medico':
            try:
                medico = Medico.objects.get(usuario=usuario)
                user_data['medico_id'] = medico.pk
            except Medico.DoesNotExist:
                pass
        elif usuario.rol == 'Administrador':
            try:
                admin = Administrador.objects.get(usuario=usuario)
                user_data['admin_id'] = admin.pk
            except Administrador.DoesNotExist:
                pass

        return Response({
            'user': user_data,
            'token': str(RefreshToken.for_user(usuario).access_token),
            'message': 'Login exitoso'
        }, status=status.HTTP_200_OK)
        
    except Usuario.DoesNotExist:
        return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e:
        print(f"❌ Error en login: {str(e)}")
        return Response({'error': 'Error interno del servidor'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login unificado para todos los roles: Paciente, Médico, Administrador
    """
    rut = (request.data.get('rut') or '').strip()
    password = request.data.get('password') or ''
    
    print(f"🔐 Intento de login - RUT: {rut}")
    
    if not rut or not password:
        return Response({'error': 'RUT y contraseña son requeridos'}, status=400)
    
    
    try:
        # Buscar el usuario por RUT
        usuario = Usuario.objects.get(rut)
        print(f"✅ Usuario encontrado: {usuario.nombre} - Rol: {usuario.rol}")
        
        # Verificar contraseña
        if not check_password(password, usuario.password):
            print(f"❌ Contraseña incorrecta para {usuario.nombre}")
            return Response({'error': 'Credenciales inválidas'}, status=401)
        
        print(f"✅ Contraseña correcta")
        
        # Preparar datos del usuario según su rol
        user_data = {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'correo': usuario.correo,
            'telefono': usuario.telefono,
            'rut': usuario.rut,
            'rol': usuario.rol
        }
        
        # Si es Paciente, agregar datos adicionales
        if usuario.rol == 'Paciente':
            try:
                paciente = Paciente.objects.get(usuario=usuario)
                user_data['paciente_id'] = paciente.usuario_id
                user_data['direccion'] = paciente.direccion
                print(f"ℹ️ Datos de paciente agregados - ID: {paciente.usuario_id}")
            except Paciente.DoesNotExist:
                # Si es paciente pero no tiene registro en tabla Paciente, crearlo
                paciente = Paciente.objects.create(
                    usuario=usuario,
                    direccion=''
                )
                user_data['paciente_id'] = paciente.usuario_id
                user_data['direccion'] = ''
                print(f"✅ Registro de paciente creado automáticamente - ID: {paciente.usuario_id}")
        
        # Si es Médico, agregar datos adicionales
        elif usuario.rol == 'Medico':
            try:
                medico = Medico.objects.get(usuario=usuario)
                user_data['medico_id'] = medico.usuario_id
                
                # Obtener especialidades del médico
                especialidades = MedicoEspecialidad.objects.filter(medico=medico, activo=True)
                user_data['especialidades'] = [
                    {
                        'id': me.especialidad.id,
                        'nombre': me.especialidad.nombre
                    }
                    for me in especialidades
                ]
                print(f"ℹ️ Datos de médico agregados - ID: {medico.usuario_id}, Especialidades: {len(user_data['especialidades'])}")
            except Medico.DoesNotExist:
                user_data['medico_id'] = None
                user_data['especialidades'] = []
                print(f"⚠️ Usuario es Médico pero no tiene registro en tabla Medico")
        
        # Generar token (puedes usar JWT si lo prefieres)
        token = f"token_{usuario.id}_{usuario.rut}"
        
        print(f"✅ Login exitoso para {usuario.nombre}")
        
        return Response({
            'user': user_data,
            'token': token,
            'message': f'Bienvenido {usuario.nombre}'
        }, status=200)
        
    except Usuario.DoesNotExist:
        print(f"❌ Usuario no encontrado con RUT: {rut_normalizado}")
        return Response({'error': 'Usuario no encontrado. Verifica tu RUT.'}, status=404)
    except Exception as e:
        import traceback
        print(f"❌ Error inesperado en login:")
        traceback.print_exc()
        return Response({'error': f'Error en el servidor: {str(e)}'}, status=500)

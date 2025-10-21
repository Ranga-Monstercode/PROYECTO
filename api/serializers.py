from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Usuario, Paciente, Administrador, Medico, MedicoEspecialidad, Cita, Notificacion, Horario, Especialidad, Box

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'correo', 'password', 'telefono', 'rut', 'rol']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'nombre': {'required': False},
            'correo': {'required': False},
            'rol': {'required': False}
        }

    def create(self, validated_data):
        # ✅ Permitir creación con solo RUT
        if 'rol' not in validated_data:
            validated_data['rol'] = 'Paciente'
        if 'nombre' not in validated_data:
            validated_data['nombre'] = f"Usuario {validated_data['rut']}"
        if 'correo' not in validated_data:
            validated_data['correo'] = f"{validated_data['rut']}@temporal.com"
        
        pwd = validated_data.pop('password', None)
        if pwd:
            validated_data['password'] = make_password(pwd)
        else:
            # ✅ Generar password temporal basado en RUT
            validated_data['password'] = make_password(validated_data['rut'])
        
        return super().create(validated_data)

class PacienteSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()
    class Meta:
        model = Paciente
        fields = ['usuario', 'direccion']
    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        usuario = UsuarioSerializer(data=usuario_data)
        usuario.is_valid(raise_exception=True)
        u = usuario.save()
        return Paciente.objects.create(usuario=u, **validated_data)
    def to_representation(self, instance):
        return {'usuario': UsuarioSerializer(instance.usuario).data, 'direccion': getattr(instance, 'direccion', '')}

class AdministradorSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()
    class Meta:
        model = Administrador
        fields = ['usuario']
    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        usuario = UsuarioSerializer(data=usuario_data)
        usuario.is_valid(raise_exception=True)
        u = usuario.save()
        return Administrador.objects.create(usuario=u)
    def to_representation(self, instance):
        return {'usuario': UsuarioSerializer(instance.usuario).data}

class EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = ['id', 'nombre', 'descripcion']

class MedicoSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    usuario = UsuarioSerializer()
    class Meta:
        model = Medico
        fields = ['id', 'usuario']
    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        usuario = UsuarioSerializer(data=usuario_data)
        usuario.is_valid(raise_exception=True)
        u = usuario.save()
        return Medico.objects.create(usuario=u, **validated_data)
    def update(self, instance, validated_data):
        usuario_data = validated_data.pop('usuario', None)
        if usuario_data:
            u_ser = UsuarioSerializer(instance=instance.usuario, data=usuario_data, partial=True)
            u_ser.is_valid(raise_exception=True)
            u_ser.save()
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

class BoxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Box
        fields = ['id', 'medico', 'nombre', 'activo']

class MedicoEspecialidadSerializer(serializers.ModelSerializer):
    medico_id = serializers.IntegerField(write_only=True, required=True)
    especialidad_id = serializers.IntegerField(write_only=True, required=True)
    medico = serializers.IntegerField(source='medico.pk', read_only=True)
    especialidad = EspecialidadSerializer(read_only=True)

    class Meta:
        model = MedicoEspecialidad
        fields = ['id', 'medico', 'medico_id', 'especialidad', 'especialidad_id', 'activo']

    def create(self, validated_data):
        medico_id = validated_data.pop('medico_id')
        especialidad_id = validated_data.pop('especialidad_id')
        medico = Medico.objects.get(pk=medico_id)
        especialidad = Especialidad.objects.get(pk=especialidad_id)
        return MedicoEspecialidad.objects.create(medico=medico, especialidad=especialidad, **validated_data)

    def update(self, instance, validated_data):
        medico_id = validated_data.pop('medico_id', None)
        especialidad_id = validated_data.pop('especialidad_id', None)
        if medico_id:
            instance.medico = Medico.objects.get(pk=medico_id)
        if especialidad_id:
            instance.especialidad = Especialidad.objects.get(pk=especialidad_id)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()
        return instance

class HorarioSerializer(serializers.ModelSerializer):
    medico_especialidad = serializers.PrimaryKeyRelatedField(queryset=MedicoEspecialidad.objects.all())
    box = serializers.PrimaryKeyRelatedField(queryset=Box.objects.all(), required=True, allow_null=False)
    box_nombre = serializers.CharField(source='box.nombre', read_only=True)

    class Meta:
        model = Horario
        fields = ['id', 'medico_especialidad', 'box', 'box_nombre', 'dia', 'horaInicio', 'horaFin']

    def validate(self, data):
        me = data['medico_especialidad']
        box = data.get('box')

        if not box:
            raise serializers.ValidationError({"box": "Debe seleccionar un box"})

        if box.medico_id != me.medico_id:
            raise serializers.ValidationError({"box": "El box seleccionado no pertenece al mismo médico"})

        if data['horaInicio'].minute not in [0, 15, 30, 45]:
            raise serializers.ValidationError({"horaInicio": "Debe ser en intervalos de 15 minutos"})
        if data['horaFin'].minute not in [0, 15, 30, 45]:
            raise serializers.ValidationError({"horaFin": "Debe ser en intervalos de 15 minutos"})
        if data['horaInicio'].hour < 8 or data['horaInicio'].hour >= 20:
            raise serializers.ValidationError({"horaInicio": "Debe estar entre 8:00 y 20:00"})
        if data['horaFin'].hour < 8 or data['horaFin'].hour > 20:
            raise serializers.ValidationError({"horaFin": "Debe estar entre 8:00 y 20:00"})
        if data['horaInicio'] >= data['horaFin']:
            raise serializers.ValidationError({"horaInicio": "Debe ser anterior a horaFin"})

        qs = Horario.objects.filter(
            medico_especialidad__medico_id=me.medico_id,
            dia=data['dia'],
            box_id=box.id
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        for h in qs:
            if (data['horaInicio'] < h.horaFin) and (h.horaInicio < data['horaFin']):
                raise serializers.ValidationError({"box": "Ya existe un horario superpuesto en este box para este médico"})
        return data

class CitaSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.usuario.nombre', read_only=True)
    medico_nombre = serializers.CharField(source='medico.usuario.nombre', read_only=True)
    especialidad_nombre = serializers.CharField(source='medico_especialidad.especialidad.nombre', read_only=True)
    box_nombre = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Cita
        fields = '__all__'
    
    def get_box_nombre(self, obj):
        """Derivar box desde Horario correspondiente"""
        try:
            me = obj.medico_especialidad
            if not me:
                return None
            dias = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']
            # ✅ Convertir a hora local de Chile antes de buscar
            from django.utils import timezone
            import pytz
            chile_tz = pytz.timezone('America/Santiago')
            fecha_chile = obj.fechaHora.astimezone(chile_tz)
            dia_nombre = dias[fecha_chile.weekday()]
            t = fecha_chile.time()
            
            h = Horario.objects.filter(
                medico_especialidad=me, 
                dia=dia_nombre, 
                horaInicio__lte=t, 
                horaFin__gt=t
            ).first()
            
            return h.box.nombre if (h and h.box) else None
        except Exception as e:
            print(f"❌ Error obteniendo box_nombre: {e}")
            return None

    def validate_fechaHora(self, value):
        if value.minute not in [0, 15, 30, 45]:
            raise serializers.ValidationError("Las citas solo pueden agendarse en intervalos de 15 minutos")
        
        if value.hour < 8 or value.hour >= 20:
            raise serializers.ValidationError("Las citas solo pueden agendarse entre 8:00 AM y 8:00 PM")
        
        return value
    
    def validate(self, data):
        # ✅ Validar que se proporcione paciente
        if 'paciente' not in data or not data['paciente']:
            raise serializers.ValidationError({
                'paciente': 'El paciente es requerido'
            })
        
        # ✅ Solo validar si se está enviando fechaHora
        if 'fechaHora' not in data:
            # Si no se está actualizando la fecha, skip validaciones de horario
            return data
            
        medico = data.get('medico', self.instance.medico if self.instance else None)
        me = data.get('medico_especialidad', self.instance.medico_especialidad if self.instance else None)
        fechaHora = data.get('fechaHora')
        paciente = data.get('paciente', self.instance.paciente if self.instance else None)
        
        # Validar que ME pertenece al médico
        if medico and me and me.medico_id != medico.pk:
            raise serializers.ValidationError(
                {"medico_especialidad": "La especialidad seleccionada no pertenece al médico"}
            )
        
        # ✅ Validar horario usando hora local de Chile
        if me and fechaHora:
            # Convertir fechaHora a zona horaria de Chile
            import pytz
            chile_tz = pytz.timezone('America/Santiago')
            
            # Si fechaHora es naive (sin timezone), asumimos que es UTC
            if timezone.is_naive(fechaHora):
                fechaHora = timezone.make_aware(fechaHora, timezone.utc)
            
            # Convertir a hora de Chile
            fecha_chile = fechaHora.astimezone(chile_tz)
            
            dias = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']
            dia_nombre = dias[fecha_chile.weekday()]
            t = fecha_chile.time()
            
            print(f"🔍 Validando horario:")
            print(f"   - fechaHora UTC: {fechaHora}")
            print(f"   - fechaHora Chile: {fecha_chile}")
            print(f"   - Día: {dia_nombre}")
            print(f"   - Hora: {t}")
            print(f"   - Medico-Especialidad ID: {me.id}")
            
            horarios_disponibles = Horario.objects.filter(
                medico_especialidad=me, 
                dia=dia_nombre, 
                horaInicio__lte=t, 
                horaFin__gt=t
            )
            
            print(f"   - Horarios encontrados: {horarios_disponibles.count()}")
            for h in horarios_disponibles:
                print(f"     * {h.dia} {h.horaInicio}-{h.horaFin} Box:{h.box.nombre if h.box else 'Sin box'}")
            
            if not horarios_disponibles.exists():
                # Mostrar todos los horarios configurados para este ME
                todos_horarios = Horario.objects.filter(medico_especialidad=me)
                print(f"❌ No hay horarios para {dia_nombre} a las {t}")
                print(f"   Horarios configurados para este médico-especialidad:")
                for h in todos_horarios:
                    print(f"     * {h.dia} {h.horaInicio}-{h.horaFin}")
                
                raise serializers.ValidationError(
                    {"fechaHora": f"El médico no tiene disponibilidad configurada para {dia_nombre} a las {t.strftime('%H:%M')}"}
                )
        
        if medico and fechaHora:
            # Verificar conflicto exacto de hora
            conflictos = Cita.objects.filter(
                medico=medico,
                fechaHora=fechaHora,
                estado__in=['Pendiente', 'Confirmada']
            )
            if self.instance:
                conflictos = conflictos.exclude(pk=self.instance.pk)
            
            if conflictos.exists():
                raise serializers.ValidationError(
                    {"fechaHora": "Ya existe una cita en este horario"}
                )
            
            # Validar conflicto en mismo box
            try:
                import pytz
                chile_tz = pytz.timezone('America/Santiago')
                if timezone.is_naive(fechaHora):
                    fechaHora = timezone.make_aware(fechaHora, timezone.utc)
                fecha_chile = fechaHora.astimezone(chile_tz)
                
                dias = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']
                dia_nombre = dias[fecha_chile.weekday()]
                t = fecha_chile.time()
                
                h = Horario.objects.filter(
                    medico_especialidad=me,
                    dia=dia_nombre,
                    horaInicio__lte=t,
                    horaFin__gt=t
                ).select_related('box').first()
                
                if h and h.box_id:
                    otras = Cita.objects.filter(
                        medico=medico,
                        fechaHora=fechaHora,
                        estado__in=['Pendiente', 'Confirmada']
                    )
                    if self.instance:
                        otras = otras.exclude(pk=self.instance.pk)
                    
                    for c in otras:
                        c_fecha_chile = c.fechaHora.astimezone(chile_tz)
                        dia2 = dias[c_fecha_chile.weekday()]
                        t2 = c_fecha_chile.time()
                        h2 = Horario.objects.filter(
                            medico_especialidad=c.medico_especialidad,
                            dia=dia2,
                            horaInicio__lte=t2,
                            horaFin__gt=t2
                        ).first()
                        if h2 and h2.box_id == h.box_id:
                            raise serializers.ValidationError(
                                {"fechaHora": "Ya existe una cita en este box a esta hora"}
                            )
            except ValidationError:
                raise
            except Exception as e:
                print(f"⚠️ Error validando conflicto de box: {e}")
                pass
        
        return data

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ['id', 'cita', 'usuario', 'tipo', 'mensaje', 'fechaEnvio', 'estado']

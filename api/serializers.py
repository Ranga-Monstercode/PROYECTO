from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Usuario, Paciente, Administrador, Medico, MedicoEspecialidad, Agenda, Cita, Notificacion, Horario, Especialidad

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'correo', 'password', 'telefono', 'rut', 'rol']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        # Hashear la contraseña aquí
        password = validated_data.pop('password', None)
        if password:
            validated_data['password'] = make_password(password)
        return super().create(validated_data)


class PacienteSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()

    class Meta:
        model = Paciente
        fields = ['usuario', 'direccion']

    def validate(self, data):
        # Validaciones básicas
        usuario_data = data.get('usuario', {})
        if not usuario_data.get('rut'):
            raise serializers.ValidationError({'usuario': {'rut': 'El RUT es requerido'}})
        if not usuario_data.get('correo'):
            raise serializers.ValidationError({'usuario': {'correo': 'El correo es requerido'}})
        return data

    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        # UsuarioSerializer.create hará el hashing
        usuario_serializer = UsuarioSerializer(data=usuario_data)
        usuario_serializer.is_valid(raise_exception=True)
        usuario = usuario_serializer.save()
        paciente = Paciente.objects.create(usuario=usuario, **validated_data)
        return paciente

    def to_representation(self, instance):
        return {
            'usuario': UsuarioSerializer(instance.usuario).data,
            'direccion': instance.direccion
        }


class AdministradorSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()

    class Meta:
        model = Administrador
        fields = ['usuario']

    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        usuario_serializer = UsuarioSerializer(data=usuario_data)
        usuario_serializer.is_valid(raise_exception=True)
        usuario = usuario_serializer.save()
        administrador = Administrador.objects.create(usuario=usuario)
        return administrador

    def to_representation(self, instance):
        return {'usuario': UsuarioSerializer(instance.usuario).data}


class EspecialidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especialidad
        fields = ['id', 'nombre', 'descripcion']


class MedicoEspecialidadSerializer(serializers.ModelSerializer):
    especialidad = EspecialidadSerializer(read_only=True)
    especialidad_id = serializers.PrimaryKeyRelatedField(source='especialidad', queryset=Especialidad.objects.all(), write_only=True)

    class Meta:
        model = MedicoEspecialidad
        fields = ['id', 'medico', 'especialidad', 'especialidad_id', 'box', 'activo']
        read_only_fields = ['medico']


class HorarioSerializer(serializers.ModelSerializer):
    medico_especialidad = serializers.PrimaryKeyRelatedField(queryset=MedicoEspecialidad.objects.all())

    class Meta:
        model = Horario
        fields = ['id', 'medico_especialidad', 'dia', 'horaInicio', 'horaFin']

    def validate(self, data):
        # leave model-level validation to model.clean() on save
        return data


class MedicoSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()
    especialidades = MedicoEspecialidadSerializer(source='medico_especialidades', many=True, required=False)

    class Meta:
        model = Medico
        fields = ['usuario', 'especialidades', 'especialidad_texto']

    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        especialidades_data = validated_data.pop('medico_especialidades', [])
        # crear usuario
        usuario_serializer = UsuarioSerializer(data=usuario_data)
        usuario_serializer.is_valid(raise_exception=True)
        usuario = usuario_serializer.save()
        medico = Medico.objects.create(usuario=usuario, **validated_data)
        # crear relaciones MedicoEspecialidad si vienen
        for esp in especialidades_data:
            especialidad = esp.get('especialidad')
            box = esp.get('box', '')
            MedicoEspecialidad.objects.create(medico=medico, especialidad=especialidad, box=box)
        return medico

    def update(self, instance, validated_data):
        usuario_data = validated_data.pop('usuario', None)
        especialidades_data = validated_data.pop('medico_especialidades', None)
        if usuario_data:
            usuario_serializer = UsuarioSerializer(instance=instance.usuario, data=usuario_data, partial=True)
            usuario_serializer.is_valid(raise_exception=True)
            usuario_serializer.save()
        if especialidades_data is not None:
            # sincronizar especialidades: eliminar/crear según payload
            instance.medico_especialidades.all().delete()
            for esp in especialidades_data:
                especialidad = esp.get('especialidad')
                box = esp.get('box', '')
                MedicoEspecialidad.objects.create(medico=instance, especialidad=especialidad, box=box)
        instance.especialidad_texto = validated_data.get('especialidad_texto', instance.especialidad_texto)
        instance.save()
        return instance


class AgendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agenda
        fields = ['id', 'medico']


class CitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cita
        fields = ['id', 'paciente', 'medico', 'agenda', 'fechaHora', 'estado', 'prioridad', 'descripcion']


class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ['id', 'cita', 'usuario', 'tipo', 'mensaje', 'fechaEnvio', 'estado']

# Haz lo mismo para los demás ViewSets si lo necesitas

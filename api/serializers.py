from rest_framework import serializers
from .models import Usuario, Paciente, Administrador, Medico, Agenda, Cita, Notificacion, Horario

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nombre', 'correo', 'password', 'telefono', 'rol','rut']
        extra_kwargs = {'password': {'write_only': True}}

class PacienteSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()

    class Meta:
        model = Paciente
        fields = ['usuario', 'direccion']

    def validate(self, data):
        usuario_data = data.get('usuario')
        if usuario_data['rol'] != 'Paciente':
            raise serializers.ValidationError("El rol debe ser 'Paciente' para registrar un paciente.")
        return data

    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        usuario = Usuario.objects.create(**usuario_data)
        paciente = Paciente.objects.create(usuario=usuario, **validated_data)
        return paciente

class AdministradorSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()
    class Meta:
        model = Administrador
        fields = ['usuario']

    def validate(self, data):
        usuario_data = data.get('usuario')
        if usuario_data['rol'] != 'Administrador':
            raise serializers.ValidationError("El rol debe ser 'Administrador' para registrar un administrador.")
        return data

    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        usuario = Usuario.objects.create(**usuario_data)
        administrador = Administrador.objects.create(usuario=usuario)
        return administrador

class MedicoSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer()
    class Meta:
        model = Medico
        fields = ['usuario', 'especialidad']
    
    def validate(self, data):
        usuario_data = data.get('usuario')
        if usuario_data['rol'] != 'Medico':
            raise serializers.ValidationError("El rol debe ser 'Medico' para registrar un médico.")
        return data

    def create(self, validated_data):
        usuario_data = validated_data.pop('usuario')
        usuario = Usuario.objects.create(**usuario_data)
        medico = Medico.objects.create(usuario=usuario, **validated_data)
        return medico

class AgendaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agenda
        fields = ['id', 'medico']

class CitaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cita
        fields = ['id', 'paciente', 'medico', 'agenda', 'fechaHora', 'estado', 'prioridad']

class NotificacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacion
        fields = ['id', 'cita', 'usuario', 'tipo', 'mensaje', 'fechaEnvio', 'estado']

class HorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Horario
        fields = ['id', 'medico', 'dia', 'horaInicio', 'horaFin']



# Haz lo mismo para los demás ViewSets si lo necesitas

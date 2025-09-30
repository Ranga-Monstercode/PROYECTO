from django.db import models
from django.contrib.auth.hashers import make_password, check_password

# Create your models here.

class Usuario(models.Model):
    ROLES = (
        ('Paciente', 'Paciente'),
        ('Administrador', 'Administrador'),
        ('Medico', 'Medico'),
    )
    nombre = models.CharField(max_length=100)
    correo = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    rut = models.CharField(max_length=12, unique=True)  # <-- Nuevo campo
    rol = models.CharField(max_length=20, choices=ROLES)

class Paciente(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)

class Administrador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)

class Medico(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    especialidad = models.CharField(max_length=100)

class Agenda(models.Model):
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE)
    # Puedes agregar más campos si lo necesitas

class Cita(models.Model):
    ESTADOS = (
        ('Pendiente', 'Pendiente'),
        ('Confirmada', 'Confirmada'),
        ('Cancelada', 'Cancelada'),
        ('Reprogramada', 'Reprogramada'),
    )
    PRIORIDAD = (
        ('Normal', 'Normal'),
        ('Urgencia', 'Urgencia'),
    )
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE)
    agenda = models.ForeignKey(Agenda, on_delete=models.SET_NULL, null=True, blank=True)
    fechaHora = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD, default='Normal')

class Notificacion(models.Model):
    TIPOS = (
        ('Email', 'Email'),
        ('SMS', 'SMS'),
    )
    ESTADOS = (
        ('Pendiente', 'Pendiente'),
        ('Enviada', 'Enviada'),
        ('Fallida', 'Fallida'),
    )
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    mensaje = models.CharField(max_length=255, blank=True, null=True)
    fechaEnvio = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='Pendiente')

class Horario(models.Model):
    DIAS = (
        ('Lunes', 'Lunes'),
        ('Martes', 'Martes'),
        ('Miercoles', 'Miercoles'),
        ('Jueves', 'Jueves'),
        ('Viernes', 'Viernes'),
        ('Sabado', 'Sabado'),
        ('Domingo', 'Domingo'),
    )
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE)
    dia = models.CharField(max_length=10, choices=DIAS)
    horaInicio = models.TimeField()
    horaFin = models.TimeField()

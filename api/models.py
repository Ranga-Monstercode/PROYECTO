from django.core.exceptions import ValidationError
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

class Especialidad(models.Model):
    """
    Modelo normalizado para especialidades médicas
    """
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Especialidad'
        verbose_name_plural = 'Especialidades'
    
    def __str__(self):
        return self.nombre

class Medico(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    # quitamos especialidad FK única; mantenemos compatibilidad
    especialidad_texto = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return f"Dr(a). {self.usuario.nombre}"

class MedicoEspecialidad(models.Model):
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='medico_especialidades')
    especialidad = models.ForeignKey(Especialidad, on_delete=models.CASCADE, related_name='medico_especialidades')
    box = models.CharField(max_length=50, blank=True, null=True)  # box / sala / consultorio
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('medico', 'especialidad')

    def __str__(self):
        return f"{self.medico.usuario.nombre} — {self.especialidad.nombre} ({self.box or 'sin box'})"

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
    descripcion = models.TextField(blank=True, null=True, help_text="Motivo o descripción de la cita")

    def __str__(self):
        return f"Cita con Dr(a). {self.medico.usuario.nombre} para {self.paciente.nombre} el {self.fechaHora}"

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
    medico_especialidad = models.ForeignKey(MedicoEspecialidad, on_delete=models.CASCADE, related_name='horarios')
    dia = models.CharField(max_length=10, choices=DIAS)
    horaInicio = models.TimeField()
    horaFin = models.TimeField()

    class Meta:
        ordering = ['medico_especialidad', 'dia', 'horaInicio']

    def clean(self):
        # validaciones básicas
        if self.horaInicio >= self.horaFin:
            raise ValidationError("horaInicio debe ser anterior a horaFin")

        # evitar solapamientos dentro del mismo medico_especialidad y día
        qs = Horario.objects.filter(
            medico_especialidad=self.medico_especialidad,
            dia=self.dia
        )
        # excluir self cuando se edita
        if self.pk:
            qs = qs.exclude(pk=self.pk)

        for h in qs:
            # overlapping check: startA < endB and startB < endA
            if (self.horaInicio < h.horaFin) and (h.horaInicio < self.horaFin):
                raise ValidationError("Horario se solapa con otro horario existente para esta especialidad/medico")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medico_especialidad} - {self.dia} {self.horaInicio}-{self.horaFin}"

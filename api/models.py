from django.core.exceptions import ValidationError
from django.db import models
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password

class Usuario(models.Model):
    ROLES = [
        ('Administrador', 'Administrador'),
        ('Medico', 'Medico'),
        ('Paciente', 'Paciente'),
    ]
    
    nombre = models.CharField(max_length=255)
    correo = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    rut = models.CharField(max_length=12, unique=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    rol = models.CharField(max_length=20, choices=ROLES)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    # Campos requeridos para JWT
    USERNAME_FIELD = 'correo'
    REQUIRED_FIELDS = ['nombre', 'rut']
    
    # ✅ Propiedades requeridas para JWT
    @property
    def is_active(self):
        return True
    
    @property
    def is_anonymous(self):
        return False
    
    @property
    def is_authenticated(self):
        return True
    
    # ✅ Para que JWT pueda obtener el username
    def get_username(self):
        return self.correo
    
    # ✅ Métodos de contraseña
    def set_password(self, raw_password):
        """Encripta la contraseña"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Verifica la contraseña"""
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.nombre} ({self.rol})"

    class Meta:
        db_table = 'usuarios'

class Paciente(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)

class Administrador(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)

class Especialidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Especialidad'
        verbose_name_plural = 'Especialidades'
    
    def __str__(self):
        return self.nombre

class Medico(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)
    especialidad_texto = models.CharField(max_length=100, blank=True, null=True)
    def __str__(self):
        return f"Dr(a). {self.usuario.nombre}"

class Box(models.Model):
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='boxes')
    nombre = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('medico', 'nombre')

    def __str__(self):
        return f"{self.nombre} ({self.medico.usuario.nombre})"

class MedicoEspecialidad(models.Model):
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE, related_name='medico_especialidades')
    especialidad = models.ForeignKey(Especialidad, on_delete=models.CASCADE, related_name='medico_especialidades')
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('medico', 'especialidad')

    def __str__(self):
        return f"{self.medico.usuario.nombre} - {self.especialidad.nombre}"

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
    box = models.ForeignKey(Box, on_delete=models.PROTECT, related_name='horarios', null=True, blank=True)  # ahora el Box se elige por horario
    dia = models.CharField(max_length=10, choices=DIAS)
    horaInicio = models.TimeField()
    horaFin = models.TimeField()

    class Meta:
        ordering = ['medico_especialidad', 'dia', 'horaInicio']

    def clean(self):
        if self.horaInicio >= self.horaFin:
            raise ValidationError("horaInicio debe ser anterior a horaFin")

        # 15 minutos y rango 8-20
        for tfield, label in [(self.horaInicio, "inicio"), (self.horaFin, "fin")]:
            if tfield.minute not in [0, 15, 30, 45]:
                raise ValidationError(f"La hora de {label} debe ser en intervalos de 15 minutos")
            if tfield.hour < 8 or (label == "inicio" and tfield.hour >= 20) or (label == "fin" and tfield.hour > 20):
                raise ValidationError("El horario debe estar entre 8:00 y 20:00")

        # Validar que el box pertenezca al mismo médico
        if self.box and self.medico_especialidad and self.box.medico_id != self.medico_especialidad.medico_id:
            raise ValidationError("El box seleccionado no pertenece al mismo médico del horario")

        # Solapes en el MISMO BOX para el mismo médico y día
        if self.box_id:
            qs = Horario.objects.filter(
                medico_especialidad__medico_id=self.medico_especialidad.medico_id,
                dia=self.dia,
                box_id=self.box_id
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            for h in qs:
                if (self.horaInicio < h.horaFin) and (h.horaInicio < self.horaFin):
                    raise ValidationError("Existe un horario superpuesto en el mismo box para este médico")

    def save(self, *args, **kwargs):
        # Asegura que clean() se ejecute al guardar
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        box_info = f"Box:{self.box.nombre}" if self.box else "Sin box"
        return f"{self.medico_especialidad} - {self.dia} {self.horaInicio}-{self.horaFin} {box_info}"

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
    # paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE)  # <-- reemplazado
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)      # <-- ahora apunta a Usuario
    medico = models.ForeignKey(Medico, on_delete=models.CASCADE)
    medico_especialidad = models.ForeignKey(MedicoEspecialidad, on_delete=models.CASCADE, related_name='citas', null=True, blank=True)
    # El box se puede derivar del Horario activo, no es obligatorio persistirlo
    fechaHora = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')
    prioridad = models.CharField(max_length=10, choices=PRIORIDAD, default='Normal')
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['fechaHora']

    def clean(self):
        """
        ✅ Solo validar si fechaHora está siendo modificada
        """
        # Si la instancia ya existe y fechaHora no cambió, skip validaciones
        if self.pk:
            try:
                old_instance = Cita.objects.get(pk=self.pk)
                # Si la fecha no cambió, no validar horario
                if old_instance.fechaHora == self.fechaHora:
                    return
            except Cita.DoesNotExist:
                pass
        
        # Validaciones de horario solo si fechaHora es nueva o cambió
        if self.fechaHora.minute not in [0, 15, 30, 45]:
            raise ValidationError("Las citas solo pueden agendarse en intervalos de 15 minutos")
        if self.fechaHora.hour < 8 or self.fechaHora.hour >= 20:
            raise ValidationError("Las citas solo pueden agendarse entre las 8:00 y 20:00")

        # Conflicto exacto por médico
        conflictos = Cita.objects.filter(
            medico=self.medico,
            fechaHora=self.fechaHora,
            estado__in=['Pendiente', 'Confirmada']
        )
        if self.pk:
            conflictos = conflictos.exclude(pk=self.pk)
        if conflictos.exists():
            raise ValidationError("Ya existe una cita en este horario para el médico")

        # Validación de conflicto en mismo box
        try:
            if self.medico_especialidad_id:
                dias = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']
                dia_nombre = dias[self.fechaHora.weekday()]
                t = self.fechaHora.time()
                h = Horario.objects.filter(
                    medico_especialidad=self.medico_especialidad,
                    dia=dia_nombre,
                    horaInicio__lte=t,
                    horaFin__gt=t
                ).select_related('box').first()
                
                if h and h.box_id:
                    otras = Cita.objects.filter(
                        medico=self.medico,
                        fechaHora=self.fechaHora,
                        estado__in=['Pendiente', 'Confirmada']
                    )
                    if self.pk:
                        otras = otras.exclude(pk=self.pk)
                    
                    for c in otras:
                        dias2 = ['Lunes','Martes','Miercoles','Jueves','Viernes','Sabado','Domingo']
                        dia2 = dias2[c.fechaHora.weekday()]
                        t2 = c.fechaHora.time()
                        h2 = Horario.objects.filter(
                            medico_especialidad=c.medico_especialidad,
                            dia=dia2,
                            horaInicio__lte=t2,
                            horaFin__gt=t2
                        ).first()
                        if h2 and h2.box_id == h.box_id:
                            raise ValidationError("Ya existe una cita en este horario en el mismo box")
        except ValidationError:
            raise
        except Exception:
            pass

    def save(self, *args, **kwargs):
        # ✅ Permitir skip de validación para actualizaciones parciales
        skip_validation = kwargs.pop('skip_validation', False)
        
        if not skip_validation:
            self.full_clean()
        
        super().save(*args, **kwargs)

class Notificacion(models.Model):
    TIPOS = (
        ('Email', 'Email'),
        ('SMS', 'SMS'),
    )
    ESTADOS = (
        ('Pendiente', 'Pendiente'),
        ('Enviada', 'Enviada'),
        ('Fallida', 'Fallida'),
        ('Completada', 'Completada'),
    )
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    mensaje = models.CharField(max_length=255, blank=True, null=True)
    fechaEnvio = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=10, choices=ESTADOS, default='Pendiente')

class Recordatorio(models.Model):
    cita = models.OneToOneField(Cita, on_delete=models.CASCADE, related_name='recordatorio')
    fecha_programada = models.DateTimeField()   # cuándo debe enviarse
    enviado = models.BooleanField(default=False)
    fecha_envio = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['fecha_programada']

    def __str__(self):
        return f"Recordatorio cita {self.cita.id} -> {self.fecha_programada} (enviado={self.enviado})"

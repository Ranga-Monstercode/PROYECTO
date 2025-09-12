from django.db import models

# Create your models here.

from django.db import models
from django.contrib.auth.hashers import make_password, check_password

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    rut = models.CharField(max_length=12, unique=True)
    correo = models.EmailField(unique=True)
    password = models.CharField(max_length=128)

    def save(self, *args, **kwargs):
        # Encriptar la contraseña antes de guardar
        if not self.pk or 'password' in kwargs.get('update_fields', []):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def verificar_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.nombre} - {self.rut}"

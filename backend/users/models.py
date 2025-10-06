from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Estudiante'),
        ('teacher', 'Profesor'),
    ]
    
    email = models.EmailField(unique=True)
    fecha_de_nacimiento = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    
    # Campo para que los profesores puedan ver estudiantes específicos
    students = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        blank=True,
        limit_choices_to={'role': 'student'},
        related_name='teachers'
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'

# Crear token automáticamente cuando se crea un usuario
@receiver(post_save, sender=CustomUser)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Estudiante'),
        ('teacher', 'Profesor'),
        ('admin', 'Administrador'),
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
    
    @property
    def is_admin(self):
        return self.role == 'admin'

# Crear token automáticamente cuando se crea un usuario
@receiver(post_save, sender=CustomUser)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


class Course(models.Model):
    """
    Modelo de Curso para organizar estudiantes y profesores.
    Los administradores pueden crear cursos y asignar profesores.
    """
    name = models.CharField(max_length=200, help_text="Nombre del curso (ej: Matemáticas 3°A)")
    code = models.CharField(max_length=50, unique=True, help_text="Código único del curso (ej: MAT3A-2025)")
    description = models.TextField(blank=True, help_text="Descripción del curso")
    
    # Profesor asignado al curso
    teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'teacher'},
        related_name='courses_teaching',
        help_text="Profesor asignado"
    )
    
    # Estudiantes inscritos
    students = models.ManyToManyField(
        CustomUser,
        limit_choices_to={'role': 'student'},
        related_name='courses_enrolled',
        blank=True,
        help_text="Estudiantes inscritos en el curso"
    )
    
    # Metadatos del curso
    start_date = models.DateField(help_text="Fecha de inicio del curso")
    end_date = models.DateField(help_text="Fecha de finalización del curso")
    is_active = models.BooleanField(default=True, help_text="Indica si el curso está activo")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date', 'name']
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def student_count(self):
        """Retorna el número de estudiantes inscritos"""
        return self.students.count()
    
    @property
    def teacher_name(self):
        """Retorna el nombre del profesor asignado"""
        return self.teacher.get_full_name() if self.teacher else "Sin asignar"
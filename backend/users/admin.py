# backend/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Configuración personalizada del admin para usuarios
    """
    list_display = (
        'username', 
        'email', 
        'role_badge', 
        'full_name_display',
        'students_count',
        'is_active_badge',
        'date_joined_short'
    )
    
    list_filter = (
        'role', 
        'is_active', 
        'is_staff', 
        'is_superuser',
        'date_joined'
    )
    
    search_fields = (
        'username', 
        'email', 
        'first_name', 
        'last_name'
    )
    
    ordering = ('-date_joined',)
    
    # Filtros en la barra lateral derecha
    date_hierarchy = 'date_joined'
    
    # Campos que se mostrarán en el formulario de edición
    fieldsets = (
        ('Información de Usuario', {
            'fields': ('username', 'password')
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email', 'fecha_de_nacimiento')
        }),
        ('Rol y Permisos', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser'),
            'classes': ('wide',)
        }),
        ('Estudiantes Asignados (Solo Profesores)', {
            'fields': ('students',),
            'classes': ('collapse',),
            'description': 'Solo aplica si el rol es Profesor'
        }),
        ('Fechas Importantes', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # Campos que se mostrarán al crear un nuevo usuario
    add_fieldsets = (
        ('Información de Acceso', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        ('Información Personal', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'fecha_de_nacimiento'),
        }),
        ('Rol', {
            'classes': ('wide',),
            'fields': ('role',),
            'description': 'Selecciona si es estudiante o profesor'
        }),
    )
    
    # Configuración del filtro de estudiantes
    filter_horizontal = ('students',)
    
    # Acciones personalizadas
    actions = [
        'activate_users',
        'deactivate_users',
        'make_teachers',
        'make_students',
    ]
    
    # --- MÉTODOS PERSONALIZADOS PARA VISUALIZACIÓN ---
    
    @admin.display(description='Rol', ordering='role')
    def role_badge(self, obj):
        """Muestra el rol con un badge de color"""
        if obj.role == 'teacher':
            color = '#28a745'  # Verde
            text = 'Profesor'
        else:
            color = '#007bff'  # Azul
            text = 'Estudiante'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{} {}</span>',
            color, text
        )
    
    @admin.display(description='Nombre Completo')
    def full_name_display(self, obj):
        """Muestra el nombre completo o N/A"""
        full_name = obj.get_full_name()
        if full_name:
            return full_name
        return format_html('<em style="color: gray;">No especificado</em>')
    
    @admin.display(description='Estudiantes Asignados', ordering='students')
    def students_count(self, obj):
        """Muestra la cantidad de estudiantes asignados (solo para profesores)"""
        if obj.is_teacher:
            count = obj.students.count()
            if count > 0:
                # Crear enlace a la lista filtrada de estudiantes
                url = reverse('admin:users_customuser_changelist') + f'?id__in={",".join(map(str, obj.students.values_list("id", flat=True)))}'
                return format_html(
                    '<a href="{}" style="color: #007bff; font-weight: bold;">{} estudiante(s)</a>',
                    url, count
                )
            else:
                return format_html('<span style="color: gray;">Sin estudiantes</span>')
        return format_html('<span style="color: gray;">N/A</span>')
    
    @admin.display(description='Estado', ordering='is_active', boolean=True)
    def is_active_badge(self, obj):
        """Muestra el estado activo/inactivo"""
        return obj.is_active
    
    @admin.display(description='Fecha de Registro', ordering='date_joined')
    def date_joined_short(self, obj):
        """Muestra la fecha de registro en formato corto"""
        return obj.date_joined.strftime('%d/%m/%Y')
    
    # --- ACCIONES PERSONALIZADAS ---
    
    @admin.action(description='Activar usuarios seleccionados')
    def activate_users(self, request, queryset):
        """Activa los usuarios seleccionados"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} usuario(s) activado(s) exitosamente.')
    
    @admin.action(description='Desactivar usuarios seleccionados')
    def deactivate_users(self, request, queryset):
        """Desactiva los usuarios seleccionados"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} usuario(s) desactivado(s) exitosamente.')
    
    @admin.action(description='Convertir a Profesores')
    def make_teachers(self, request, queryset):
        """Convierte los usuarios seleccionados en profesores"""
        updated = queryset.update(role='teacher')
        self.message_user(request, f'{updated} usuario(s) convertido(s) a profesor(es).')
    
    @admin.action(description='Convertir a Estudiantes')
    def make_students(self, request, queryset):
        """Convierte los usuarios seleccionados en estudiantes"""
        # Limpiar estudiantes asignados si tenían
        for user in queryset.filter(role='teacher'):
            user.students.clear()
        updated = queryset.update(role='student')
        self.message_user(request, f'{updated} usuario(s) convertido(s) a estudiante(s).')
    
    # --- CONFIGURACIÓN ADICIONAL ---
    
    def get_queryset(self, request):
        """Optimiza las queries para evitar N+1"""
        qs = super().get_queryset(request)
        return qs.prefetch_related('students')
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtra el campo 'students' para mostrar solo estudiantes"""
        if db_field.name == "students":
            kwargs["queryset"] = CustomUser.objects.filter(role='student')
        return super().formfield_for_manytomany(db_field, request, **kwargs)

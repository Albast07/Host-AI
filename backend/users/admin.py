# backend/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import CustomUser


class CustomUserAdmin(BaseUserAdmin):
    """
    Admin personalizado para usuarios
    """
    # Campos a mostrar en la lista
    list_display = (
        'username', 
        'email', 
        'role', 
        'first_name',
        'last_name',
        'is_active',
        'date_joined'
    )
    
    # Filtros laterales
    list_filter = (
        'role', 
        'is_active', 
        'is_staff',
        'date_joined'
    )
    
    # Campos de búsqueda
    search_fields = (
        'username', 
        'email', 
        'first_name', 
        'last_name'
    )
    
    # Ordenamiento por defecto
    ordering = ('-date_joined',)
    
    # Campos en el formulario de edición
    fieldsets = (
        ('Información de Usuario', {
            'fields': ('username', 'password')
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email', 'fecha_de_nacimiento')
        }),
        ('Rol y Permisos', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Estudiantes Asignados', {
            'fields': ('students',),
            'classes': ('collapse',),
            'description': 'Solo para profesores'
        }),
        ('Fechas', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # Campos al crear usuario nuevo
    add_fieldsets = (
        ('Crear Usuario', {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'role'),
        }),
        ('Información Personal (Opcional)', {
            'classes': ('wide',),
            'fields': ('first_name', 'last_name', 'email', 'fecha_de_nacimiento'),
        }),
    )
    
    # Selector horizontal para estudiantes
    filter_horizontal = ('students',)
    
    # Acciones masivas
    actions = ['activar_usuarios', 'desactivar_usuarios']
    
    def activar_usuarios(self, request, queryset):
        """Activa usuarios seleccionados"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} usuario(s) activado(s).')
    activar_usuarios.short_description = 'Activar usuarios seleccionados'
    
    def desactivar_usuarios(self, request, queryset):
        """Desactiva usuarios seleccionados"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} usuario(s) desactivado(s).')
    desactivar_usuarios.short_description = 'Desactivar usuarios seleccionados'
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtrar solo estudiantes en el campo students"""
        if db_field.name == "students":
            kwargs["queryset"] = CustomUser.objects.filter(role='student')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# Registrar el modelo
admin.site.register(CustomUser, CustomUserAdmin)

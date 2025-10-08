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
        'get_students_count',
        'get_is_admin',
        'is_active',
        'date_joined'
    )
    
    # Filtros laterales
    list_filter = (
        'role', 
        'is_active', 
        'is_staff',
        'is_superuser',
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
    actions = ['activar_usuarios', 'desactivar_usuarios', 'convertir_a_profesores', 'convertir_a_estudiantes']
    
    # --- MÉTODOS PERSONALIZADOS ---
    
    def get_students_count(self, obj):
        """Muestra la cantidad de estudiantes asignados (solo profesores)"""
        if obj.role == 'teacher':
            count = obj.students.count()
            if count > 0:
                return format_html('<strong>{}</strong>', count)
            else:
                return '-'
        return 'N/A'
    get_students_count.short_description = 'Estudiantes Asignados'
    get_students_count.admin_order_field = 'students'
    
    def get_is_admin(self, obj):
        """Muestra si el usuario es administrador"""
        if obj.is_superuser:
            return format_html(
                '<span style="background-color: #dc3545; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-weight: bold; font-size: 11px;">'
                'SUPERADMIN</span>'
            )
        elif obj.is_staff:
            return format_html(
                '<span style="background-color: #ffc107; color: #000; '
                'padding: 3px 10px; border-radius: 3px; font-weight: bold; font-size: 11px;">'
                'STAFF</span>'
            )
        else:
            return '-'
    get_is_admin.short_description = 'Admin'
    get_is_admin.admin_order_field = 'is_superuser'
    
    # --- ACCIONES MASIVAS ---
    
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
    
    def convertir_a_profesores(self, request, queryset):
        """Convierte usuarios a profesores"""
        count = queryset.update(role='teacher')
        self.message_user(request, f'{count} usuario(s) ahora son profesores.')
    convertir_a_profesores.short_description = 'Convertir a Profesores'
    
    def convertir_a_estudiantes(self, request, queryset):
        """Convierte usuarios a estudiantes y limpia asignaciones"""
        for user in queryset.filter(role='teacher'):
            user.students.clear()
        count = queryset.update(role='student')
        self.message_user(request, f'{count} usuario(s) ahora son estudiantes.')
    convertir_a_estudiantes.short_description = 'Convertir a Estudiantes'
    
    def get_queryset(self, request):
        """Optimiza las queries"""
        qs = super().get_queryset(request)
        return qs.prefetch_related('students')
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filtrar solo estudiantes en el campo students"""
        if db_field.name == "students":
            kwargs["queryset"] = CustomUser.objects.filter(role='student')
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# Registrar el modelo
admin.site.register(CustomUser, CustomUserAdmin)

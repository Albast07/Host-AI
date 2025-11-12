# backend/chat/admin.py
import json

from django.contrib import admin
from django.utils.html import format_html

from .models import Conversation, CourseEmotionRecommendation, Message

# Los modelos de Conversation y Message NO se registran en el admin
# para proteger la privacidad de los estudiantes.
# Solo el equipo técnico con acceso directo a la base de datos puede ver estos datos.

# Si en el futuro se necesita acceso, descomentar las siguientes líneas:
# admin.site.register(Conversation)
# admin.site.register(Message)


@admin.register(CourseEmotionRecommendation)
class CourseEmotionRecommendationAdmin(admin.ModelAdmin):
    """
    Permite a administradores y equipo pedagógico revisar el historial de
    recomendaciones que genera la IA para cada curso.
    """
    list_display = (
        'course',
        'triggered_emotion',
        'emotion_ratio_percent',
        'time_window_days',
        'created_at',
        'generated_by',
    )
    list_filter = ('triggered_emotion', 'time_window_days', 'created_at')
    search_fields = (
        'course__code',
        'course__name',
        'generated_by__username',
        'generated_by__first_name',
        'generated_by__last_name',
    )
    readonly_fields = (
        'course',
        'generated_by',
        'triggered_emotion',
        'emotion_ratio_percent',
        'time_window_days',
        'overview',
        'suggestions_pretty',
        'stats_snapshot_pretty',
        'disclaimer',
        'created_at',
    )
    ordering = ('-created_at',)
    fieldsets = (
        ('Curso y contexto', {
            'fields': ('course', 'generated_by', 'triggered_emotion', 'emotion_ratio_percent', 'time_window_days', 'created_at')
        }),
        ('Resumen pedagógico', {
            'fields': ('overview', 'suggestions_pretty', 'stats_snapshot_pretty', 'disclaimer')
        }),
    )

    def emotion_ratio_percent(self, obj):
        return f"{obj.emotion_ratio * 100:.1f}%"
    emotion_ratio_percent.short_description = 'Emoción disparadora'

    def suggestions_pretty(self, obj):
        data = json.dumps(obj.suggestions, indent=2, ensure_ascii=False)
        return format_html('<pre style="white-space: pre-wrap">{}</pre>', data)
    suggestions_pretty.short_description = 'Sugerencias'

    def stats_snapshot_pretty(self, obj):
        data = json.dumps(obj.stats_snapshot, indent=2, ensure_ascii=False)
        return format_html('<pre style="white-space: pre-wrap; max-height: 400px; overflow:auto;">{}</pre>', data)
    stats_snapshot_pretty.short_description = 'Métricas utilizadas'

    def has_add_permission(self, request):
        # Las recomendaciones se generan desde la API/servicio, no manualmente.
        return False
# backend/chat/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from .models import Conversation, Message
from chat.emotion_analyzer import EMOTION_MAPPING, SENTIMENT_MAPPING


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Admin para gestionar conversaciones
    """
    list_display = (
        'id',
        'user_link',
        'user_role_badge',
        'start_time_formatted',
        'messages_count_display',
        'last_message_preview',
        'emotion_summary'
    )
    
    list_filter = (
        'start_time',
        'user__role',
    )
    
    search_fields = (
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
    )
    
    readonly_fields = (
        'user',
        'start_time',
        'messages_summary',
        'emotion_distribution'
    )
    
    ordering = ('-start_time',)
    date_hierarchy = 'start_time'
    
    # --- MÉTODOS DE VISUALIZACIÓN ---
    
    @admin.display(description='Usuario', ordering='user__username')
    def user_link(self, obj):
        """Link al usuario"""
        from django.urls import reverse
        url = reverse('admin:users_customuser_change', args=[obj.user.id])
        return format_html(
            '<a href="{}" style="font-weight: bold;">{}</a>',
            url, obj.user.username
        )
    
    @admin.display(description='Rol')
    def user_role_badge(self, obj):
        """Badge del rol del usuario"""
        if obj.user.is_teacher:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 2px 8px; border-radius: 3px; font-size: 11px;">Profesor</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #007bff; color: white; '
                'padding: 2px 8px; border-radius: 3px; font-size: 11px;">🎓 Estudiante</span>'
            )
    
    @admin.display(description='Fecha de Inicio', ordering='start_time')
    def start_time_formatted(self, obj):
        """Fecha formateada"""
        return obj.start_time.strftime('%d/%m/%Y %H:%M')
    
    @admin.display(description='Mensajes')
    def messages_count_display(self, obj):
        """Cantidad de mensajes con badge"""
        count = obj.messages.count()
        user_msgs = obj.messages.filter(sender='user').count()
        bot_msgs = obj.messages.filter(sender='bot').count()
        
        return format_html(
            '<strong>{}</strong> total<br>'
            '<small style="color: #666;"> {user} |  {bot}</small>',
            count, user=user_msgs, bot=bot_msgs
        )
    
    @admin.display(description='Último Mensaje')
    def last_message_preview(self, obj):
        """Preview del último mensaje"""
        last_msg = obj.messages.order_by('-timestamp').first()
        if last_msg:
            preview = last_msg.text[:50] + '...' if len(last_msg.text) > 50 else last_msg.text
            sender_icon = '' if last_msg.sender == 'user' else ''
            return format_html(
                '<small>{} <em>{}</em></small>',
                sender_icon, preview
            )
        return format_html('<em style="color: gray;">Sin mensajes</em>')
    
    @admin.display(description='Emociones')
    def emotion_summary(self, obj):
        """Resumen de emociones predominantes"""
        user_messages = obj.messages.filter(sender='user')
        
        if not user_messages.exists():
            return format_html('<em style="color: gray;">Sin análisis</em>')
        
        # Obtener emoción más común
        emotion_counts = {}
        for msg in user_messages:
            if msg.dominant_emotion:
                emotion = EMOTION_MAPPING.get(msg.dominant_emotion, msg.dominant_emotion)
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        if emotion_counts:
            top_emotion = max(emotion_counts, key=emotion_counts.get)
            return format_html(
                '<span style="background-color: #ffc107; color: #000; '
                'padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                top_emotion.capitalize()
            )
        
        return format_html('<em style="color: gray;">N/A</em>')
    
    @admin.display(description='Resumen de Mensajes')
    def messages_summary(self, obj):
        """Resumen detallado de mensajes"""
        user_msgs = obj.messages.filter(sender='user')
        bot_msgs = obj.messages.filter(sender='bot')
        
        html = f"""
        <div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">
            <h4>Estadísticas de la Conversación</h4>
            <ul>
                <li><strong>Total de mensajes:</strong> {obj.messages.count()}</li>
                <li><strong>Mensajes del usuario:</strong> {user_msgs.count()}</li>
                <li><strong>Respuestas del bot:</strong> {bot_msgs.count()}</li>
                <li><strong>Duración:</strong> {obj.start_time.strftime('%d/%m/%Y %H:%M')}</li>
            </ul>
        </div>
        """
        return format_html(html)
    
    @admin.display(description='Distribución Emocional')
    def emotion_distribution(self, obj):
        """Gráfico de distribución emocional"""
        user_messages = obj.messages.filter(sender='user')
        
        if not user_messages.exists():
            return format_html('<p style="color: gray;"><em>Sin mensajes para analizar</em></p>')
        
        # Contar emociones
        emotion_counts = {}
        for msg in user_messages:
            if msg.dominant_emotion:
                emotion = EMOTION_MAPPING.get(msg.dominant_emotion, msg.dominant_emotion)
                emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        # Crear barras visuales
        total = sum(emotion_counts.values())
        html_bars = '<div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">'
        html_bars += '<h4>Distribución de Emociones</h4>'
        
        emotion_colors = {
            'alegría': '#28a745',
            'tristeza': '#6c757d',
            'enojo': '#dc3545',
            'miedo': '#ffc107',
            'disgusto': '#6f42c1',
            'sorpresa': '#17a2b8',
            'neutral': '#ced4da'
        }
        
        for emotion, count in sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total) * 100
            color = emotion_colors.get(emotion, '#6c757d')
            html_bars += f"""
            <div style="margin: 5px 0;">
                <strong>{emotion.capitalize()}:</strong> {count} ({percentage:.1f}%)
                <div style="background-color: #e9ecef; border-radius: 3px; height: 20px; margin-top: 3px;">
                    <div style="background-color: {color}; width: {percentage}%; height: 100%; border-radius: 3px;"></div>
                </div>
            </div>
            """
        
        html_bars += '</div>'
        return format_html(html_bars)
    
    def get_queryset(self, request):
        """Optimizar queries"""
        qs = super().get_queryset(request)
        return qs.select_related('user').prefetch_related('messages')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin para gestionar mensajes individuales
    """
    list_display = (
        'id',
        'conversation_link',
        'sender_badge',
        'message_preview',
        'emotion_badge',
        'sentiment_badge',
        'timestamp_formatted'
    )
    
    list_filter = (
        'sender',
        'dominant_emotion',
        'sentiment',
        'timestamp',
    )
    
    search_fields = (
        'text',
        'conversation__user__username',
        'conversation__user__email',
    )
    
    readonly_fields = (
        'conversation',
        'sender',
        'text',
        'timestamp',
        'emotion_analysis_display',
        'sentiment_analysis_display'
    )
    
    ordering = ('-timestamp',)
    date_hierarchy = 'timestamp'
    
    # --- MÉTODOS DE VISUALIZACIÓN ---
    
    @admin.display(description='Conversación', ordering='conversation')
    def conversation_link(self, obj):
        """Link a la conversación"""
        from django.urls import reverse
        url = reverse('admin:chat_conversation_change', args=[obj.conversation.id])
        return format_html(
            '<a href="{}">Conv #{} - {}</a>',
            url, obj.conversation.id, obj.conversation.user.username
        )
    
    @admin.display(description='Emisor')
    def sender_badge(self, obj):
        """Badge del emisor"""
        if obj.sender == 'user':
            return format_html(
                '<span style="background-color: #007bff; color: white; '
                'padding: 2px 8px; border-radius: 3px; font-size: 11px;">👤 Usuario</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #6c757d; color: white; '
                'padding: 2px 8px; border-radius: 3px; font-size: 11px;">🤖 Bot</span>'
            )
    
    @admin.display(description='Mensaje')
    def message_preview(self, obj):
        """Preview del mensaje"""
        preview = obj.text[:60] + '...' if len(obj.text) > 60 else obj.text
        return format_html('<span title="{}">{}</span>', obj.text, preview)
    
    @admin.display(description='Emoción')
    def emotion_badge(self, obj):
        """Badge de emoción"""
        if obj.sender == 'bot' or not obj.dominant_emotion:
            return format_html('<span style="color: gray;">N/A</span>')
        
        emotion_es = EMOTION_MAPPING.get(obj.dominant_emotion, obj.dominant_emotion)
        emotion_colors = {
            'alegría': '#28a745',
            'tristeza': '#6c757d',
            'enojo': '#dc3545',
            'miedo': '#ffc107',
            'disgusto': '#6f42c1',
            'sorpresa': '#17a2b8',
            'neutral': '#ced4da'
        }
        color = emotion_colors.get(emotion_es, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, emotion_es.capitalize()
        )
    
    @admin.display(description='Sentimiento')
    def sentiment_badge(self, obj):
        """Badge de sentimiento"""
        if obj.sender == 'bot' or not obj.sentiment:
            return format_html('<span style="color: gray;">N/A</span>')
        
        sentiment_es = SENTIMENT_MAPPING.get(obj.sentiment, obj.sentiment)
        sentiment_colors = {
            'positivo': '#28a745',
            'negativo': '#dc3545',
            'neutral': '#6c757d'
        }
        color = sentiment_colors.get(sentiment_es, '#6c757d')
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, sentiment_es.capitalize()
        )
    
    @admin.display(description='Fecha', ordering='timestamp')
    def timestamp_formatted(self, obj):
        """Fecha formateada"""
        return obj.timestamp.strftime('%d/%m/%Y %H:%M')
    
    @admin.display(description='Análisis Emocional Completo')
    def emotion_analysis_display(self, obj):
        """Muestra el análisis emocional completo"""
        if obj.sender == 'bot':
            return format_html('<p style="color: gray;"><em>No aplica para mensajes del bot</em></p>')
        
        html = '<div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">'
        html += '<h4>🎭 Análisis de Emociones</h4>'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr><th style="text-align: left; padding: 5px; border-bottom: 1px solid #dee2e6;">Emoción</th>'
        html += '<th style="text-align: right; padding: 5px; border-bottom: 1px solid #dee2e6;">Score</th></tr>'
        
        emotions = [
            ('Alegría', obj.emotion_joy_score),
            ('Tristeza', obj.emotion_sadness_score),
            ('Enojo', obj.emotion_anger_score),
            ('Miedo', obj.emotion_fear_score),
            ('Disgusto', obj.emotion_disgust_score),
            ('Sorpresa', obj.emotion_surprise_score),
            ('Neutral', obj.emotion_others_score),
        ]
        
        for emotion_name, score in emotions:
            if score and score > 0:
                percentage = score * 100
                html += f'<tr><td style="padding: 5px;">{emotion_name}</td>'
                html += f'<td style="text-align: right; padding: 5px;"><strong>{percentage:.1f}%</strong></td></tr>'
        
        html += '</table></div>'
        return format_html(html)
    
    @admin.display(description='Análisis de Sentimiento Completo')
    def sentiment_analysis_display(self, obj):
        """Muestra el análisis de sentimiento completo"""
        if obj.sender == 'bot':
            return format_html('<p style="color: gray;"><em>No aplica para mensajes del bot</em></p>')
        
        html = '<div style="padding: 10px; background-color: #f8f9fa; border-radius: 5px;">'
        html += '<h4>Análisis de Sentimiento</h4>'
        html += '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr><th style="text-align: left; padding: 5px; border-bottom: 1px solid #dee2e6;">Sentimiento</th>'
        html += '<th style="text-align: right; padding: 5px; border-bottom: 1px solid #dee2e6;">Score</th></tr>'
        
        sentiments = [
            ('Positivo', obj.sentiment_pos_score),
            ('Negativo', obj.sentiment_neg_score),
            ('Neutral', obj.sentiment_neu_score),
        ]
        
        for sentiment_name, score in sentiments:
            if score and score > 0:
                percentage = score * 100
                html += f'<tr><td style="padding: 5px;">{sentiment_name}</td>'
                html += f'<td style="text-align: right; padding: 5px;"><strong>{percentage:.1f}%</strong></td></tr>'
        
        html += '</table></div>'
        return format_html(html)
    
    def get_queryset(self, request):
        """Optimizar queries"""
        qs = super().get_queryset(request)
        return qs.select_related('conversation', 'conversation__user')

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Conversation, Message
from .serializers import ChatResponseSerializer
from .emotion_analyzer import EmotionAnalyzer, EMOTION_MAPPING, SENTIMENT_MAPPING
import google.generativeai as genai
import os
from django.db.models import Count
from datetime import timedelta
from django.utils import timezone

# Configurar Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Crear modelo Gemini 2.5 Flash
model = genai.GenerativeModel('gemini-2.5-flash')

# Crear analizador de emociones (Hugging Face API - pysentimiento)
emotion_analyzer = EmotionAnalyzer()

# Diccionarios de traducción
EMOTION_TRANSLATIONS = {
    "joy": "alegría",
    "sadness": "tristeza",
    "anger": "enojo",
    "fear": "miedo",
    "disgust": "disgusto",
    "surprise": "sorpresa",
    "others": "neutral"
}

SENTIMENT_TRANSLATIONS = {
    "POS": "positivo",
    "NEG": "negativo",
    "NEU": "neutral"
}

class ChatAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_emotion_tip(self, emotion):
        """Retorna un tip educativo sobre la emoción detectada"""
        tips = {
            "alegría": "La alegría nos conecta con lo positivo. ¿Qué puedes hacer para cultivar más momentos así?",
            "tristeza": "La tristeza es válida y nos ayuda a procesar pérdidas o decepciones. Date permiso de sentirla.",
            "enojo": "El enojo nos indica que algo no está bien o cruzó un límite. ¿Qué necesitas comunicar?",
            "miedo": "El miedo nos alerta ante peligros. ¿Es un miedo real o anticipado? Identificarlo ayuda.",
            "disgusto": "El disgusto nos aleja de lo que nos hace daño. ¿Qué límite necesitas establecer?",
            "sorpresa": "La sorpresa nos mantiene alertas ante lo inesperado. ¿Esta sorpresa es agradable o incómoda?",
            "neutral": "La calma y la neutralidad también son válidas. No siempre necesitamos emociones intensas."
        }
        return tips.get(emotion, "Reconocer tus emociones es el primer paso del autoconocimiento emocional.")

    def _build_context_prompt(self, conversation, current_text, emotion_es, sentiment_es):
        """Construye el prompt educativo con contexto emocional para Gemini"""
        
        # Obtener historial reciente (últimos 7 mensajes)
        recent_messages = conversation.messages.order_by('-timestamp')[:7]
        history = []
        
        for msg in reversed(recent_messages):
            role = "Estudiante" if msg.sender == 'user' else "Tú"
            history.append(f"{role}: {msg.text}")
        
        context = "\n".join(history) if history else "Esta es la primera interacción."
        
        # Construir prompt educativo
        prompt = f"""Eres un asistente educativo de inteligencia emocional para estudiantes de 12 a 18 años. Tu objetivo es ayudarles a IDENTIFICAR, NOMBRAR y COMPRENDER sus emociones mediante diálogos reflexivos.

IMPORTANTE: No eres un psicólogo ni terapeuta. Eres una herramienta educativa complementaria para el autoconocimiento emocional. No das terapia, enseñas a reconocer emociones.

CONTEXTO DE LA CONVERSACIÓN:
{context}

MENSAJE ACTUAL DEL ESTUDIANTE:
"{current_text}"

ANÁLISIS EMOCIONAL DETECTADO:
- Emoción percibida: {emotion_es}
- Tono general: {sentiment_es}

TU ENFOQUE EDUCATIVO:
1. **Validar y nombrar emociones**: Ayuda al estudiante a identificar lo que siente ("Percibo que podría haber tristeza en lo que compartes...")
2. **Preguntas reflexivas**: Haz preguntas que los ayuden a explorar sus emociones:
   - "¿En qué parte de tu cuerpo sientes eso?"
   - "¿Cuándo empezaste a sentirte así?"
   - "¿Qué situación específica disparó esta emoción?"
   - "Si tuvieras que ponerle un color a lo que sientes, ¿cuál sería?"
3. **Educación emocional**: Explica brevemente por qué es normal sentir ciertas emociones
4. **Promover autoconocimiento**: No des soluciones directas, guía al estudiante a sus propias conclusiones
5. **Lenguaje apropiado**: Usa lenguaje cercano y auténtico para adolescentes, sin ser condescendiente
6. **Brevedad**: Máximo 3-4 oraciones por respuesta
7. **Normalizar emociones**: Todas las emociones son válidas, incluso las incómodas

EJEMPLOS DE RESPUESTAS EDUCATIVAS:
- "Percibo preocupación en tu mensaje. Es totalmente normal sentir ansiedad antes de un examen, especialmente si es importante para ti. ¿Qué parte del examen te genera más inquietud?"
- "Veo alegría en lo que compartes, ¿qué crees que provocó ese sentimiento? Reconocer qué nos hace felices es parte del autoconocimiento."
- "Hay frustración en tu mensaje. Es natural sentirse así cuando algo no sale como esperabas. ¿Cómo se manifiesta físicamente esa frustración en ti?"
- "Noto tristeza. Esa emoción nos ayuda a procesar decepciones. ¿Desde cuándo te sientes así? ¿Hay algo específico que la desencadenó?"

NO HAGAS:
- No minimices las emociones ("no es para tanto", "otros están peor")
- No des consejos directos no solicitados
- No uses frases como "deberías" o "tienes que"
- No actúes como terapeuta ni des diagnósticos

Responde al estudiante de forma educativa, reflexiva y validando sus emociones:"""
        
        return prompt

    def _generate_gemini_response(self, prompt):
        """Genera respuesta usando Gemini con manejo de errores"""
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error con Gemini: {e}")
            return "Disculpa, estoy teniendo dificultades para responder en este momento. ¿Podrías reformular tu mensaje?"

    def post(self, request, *args, **kwargs):
        text = request.data.get('text')
        conversation_id = request.data.get('conversation_id')

        if not text:
            return Response({
                "error": "text is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        if not user.is_student:
            return Response({
                "error": "Solo los estudiantes pueden usar el chat."
            }, status=status.HTTP_403_FORBIDDEN)

        # Encontrar o crear conversación
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id, 
                    user=user
                )
            except Conversation.DoesNotExist:
                return Response({
                    "error": "Conversation not found or does not belong to the user."
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            conversation = Conversation.objects.create(user=user)

        # Guardar mensaje del usuario
        user_message = Message.objects.create(
            conversation=conversation,
            text=text,
            sender='user'
        )

        # ===== USAR HUGGING FACE API (pysentimiento) PARA ANÁLISIS EMOCIONAL =====
        print(f"🔍 Analizando mensaje con Hugging Face (pysentimiento)...")
        hf_analysis = emotion_analyzer.analyze_complete(text)
        
        # Extraer resultados del análisis
        emotion_data = hf_analysis['emotion_analysis']
        sentiment_data = hf_analysis['sentiment_analysis']
        
        emotion = emotion_data['dominant_emotion']
        emotion_scores = emotion_data['emotions']
        emotion_confidence = emotion_data['confidence']
        
        sentiment = sentiment_data['sentiment']
        sentiment_scores = sentiment_data['scores']
        sentiment_confidence = sentiment_data['confidence']
        
        intensity_level = hf_analysis['intensity']
        
        print(f"✅ Análisis completado: Emoción={emotion}, Sentimiento={sentiment}")
        
        # ===== GUARDAR ANÁLISIS EN LA BASE DE DATOS =====
        # Actualizar mensaje con análisis emocional detallado
        user_message.dominant_emotion = emotion
        user_message.emotion_joy_score = emotion_scores.get('joy', 0.0)
        user_message.emotion_sadness_score = emotion_scores.get('sadness', 0.0)
        user_message.emotion_anger_score = emotion_scores.get('anger', 0.0)
        user_message.emotion_fear_score = emotion_scores.get('fear', 0.0)
        user_message.emotion_disgust_score = emotion_scores.get('disgust', 0.0)
        user_message.emotion_surprise_score = emotion_scores.get('surprise', 0.0)
        user_message.emotion_others_score = emotion_scores.get('others', 0.0)
        
        # Actualizar sentimiento
        user_message.sentiment = sentiment
        user_message.sentiment_pos_score = sentiment_scores.get('POS', 0.0)
        user_message.sentiment_neg_score = sentiment_scores.get('NEG', 0.0)
        user_message.sentiment_neu_score = sentiment_scores.get('NEU', 0.0)
        
        user_message.save()
        print(f"💾 Análisis guardado en base de datos")

        # Traducir resultados a español
        dominant_emotion_es = EMOTION_MAPPING.get(emotion, emotion)
        dominant_sentiment_es = SENTIMENT_MAPPING.get(sentiment, sentiment)

        # ===== GENERAR RESPUESTA EMPÁTICA CON GEMINI =====
        print(f"🤖 Generando respuesta con Gemini...")
        prompt = self._build_context_prompt(
            conversation=conversation,
            current_text=text,
            emotion_es=dominant_emotion_es,
            sentiment_es=dominant_sentiment_es
        )
        
        bot_text = self._generate_gemini_response(prompt)
        print(f"✅ Respuesta generada")
        
        # Guardar respuesta del bot
        Message.objects.create(
            conversation=conversation,
            text=bot_text,
            sender='bot'
        )

        # ===== PREPARAR RESPUESTA PARA EL FRONTEND =====
        response_data = {
            "bot_response": bot_text,
            "conversation_id": conversation.id,
            "emotional_insight": {
                "primary_emotion": dominant_emotion_es,
                "intensity": intensity_level,
                "educational_tip": self._get_emotion_tip(dominant_emotion_es)
            },
            "user_message_analysis": {
                "text": text,
                "sentiment": {
                    "dominant": dominant_sentiment_es,
                    "Positivo": round(sentiment_scores.get('POS', 0) * 100, 1),
                    "Negativo": round(sentiment_scores.get('NEG', 0) * 100, 1),
                    "Neutral": round(sentiment_scores.get('NEU', 0) * 100, 1),
                },
                "emotions": {
                    "dominant": dominant_emotion_es,
                    "Alegria": round(emotion_scores.get('joy', 0) * 100, 1),
                    "Tristeza": round(emotion_scores.get('sadness', 0) * 100, 1),
                    "Enojo": round(emotion_scores.get('anger', 0) * 100, 1),
                    "Miedo": round(emotion_scores.get('fear', 0) * 100, 1),
                    "Disgusto": round(emotion_scores.get('disgust', 0) * 100, 1),
                    "Sorpresa": round(emotion_scores.get('surprise', 0) * 100, 1),
                    "Otros": round(emotion_scores.get('others', 0) * 100, 1),
                }
            }
        }
        
        serializer = ChatResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def get(self, request, *args, **kwargs):
        """Obtener historial de conversaciones"""
        user = request.user
        
        if not user.is_student:
            return Response({
                "error": "Solo los estudiantes pueden ver conversaciones."
            }, status=status.HTTP_403_FORBIDDEN)

        conversation_id = request.query_params.get('conversation_id')
        
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=user)
                messages = conversation.messages.all().order_by('timestamp')
                
                messages_data = []
                for message in messages:
                    message_data = {
                        'id': message.id,
                        'text': message.text,
                        'sender': message.sender,
                        'timestamp': message.timestamp,
                    }
                    
                    if message.sender == 'user':
                        message_data['analysis'] = {
                            'dominant_emotion': EMOTION_MAPPING.get(message.dominant_emotion, message.dominant_emotion),
                            'sentiment': SENTIMENT_MAPPING.get(message.sentiment, message.sentiment),
                            'emotions': {
                                'joy': round(message.emotion_joy_score * 100, 1) if message.emotion_joy_score else 0,
                                'sadness': round(message.emotion_sadness_score * 100, 1) if message.emotion_sadness_score else 0,
                                'anger': round(message.emotion_anger_score * 100, 1) if message.emotion_anger_score else 0,
                                'fear': round(message.emotion_fear_score * 100, 1) if message.emotion_fear_score else 0,
                                'disgust': round(message.emotion_disgust_score * 100, 1) if message.emotion_disgust_score else 0,
                                'surprise': round(message.emotion_surprise_score * 100, 1) if message.emotion_surprise_score else 0,
                                'others': round(message.emotion_others_score * 100, 1) if message.emotion_others_score else 0,
                            },
                            'sentiments': {
                                'positive': round(message.sentiment_pos_score * 100, 1) if message.sentiment_pos_score else 0,
                                'negative': round(message.sentiment_neg_score * 100, 1) if message.sentiment_neg_score else 0,
                                'neutral': round(message.sentiment_neu_score * 100, 1) if message.sentiment_neu_score else 0,
                            }
                        }
                    
                    messages_data.append(message_data)
                
                return Response({
                    'conversation_id': conversation.id,
                    'start_time': conversation.start_time,
                    'messages': messages_data
                }, status=status.HTTP_200_OK)
                
            except Conversation.DoesNotExist:
                return Response({
                    "error": "Conversación no encontrada."
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Listar conversaciones
        conversations = Conversation.objects.filter(user=user).order_by('-start_time')
        
        conversations_data = []
        for conv in conversations:
            last_message = conv.messages.last()
            conversations_data.append({
                'id': conv.id,
                'start_time': conv.start_time,
                'messages_count': conv.messages.count(),
                'last_message': last_message.text if last_message else None,
                'last_message_time': last_message.timestamp if last_message else None
            })

        return Response({
            'conversations': conversations_data
        }, status=status.HTTP_200_OK)
    
class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Endpoint para obtener estadísticas del dashboard.
        - Estudiantes: ven sus propias estadísticas
        - Profesores: ven estadísticas agregadas de sus estudiantes asignados
        """
        user = request.user
        
        if user.is_student:
            # Estadísticas del estudiante
            conversations = Conversation.objects.filter(user=user)
            user_messages = Message.objects.filter(
                conversation__in=conversations,
                sender='user'
            )
            
            total_entries = user_messages.count()
            
            # Mensajes de la última semana
            one_week_ago = timezone.now() - timedelta(days=7)
            entries_last_week = user_messages.filter(timestamp__gte=one_week_ago).count()
            
            # Distribución de sentimientos
            sentiment_counts = user_messages.values('sentiment').annotate(
                count=Count('sentiment')
            ).order_by('-count')
            
            sentiment_distribution = []
            for item in sentiment_counts:
                if item['sentiment']:
                    sentiment_es = SENTIMENT_MAPPING.get(item['sentiment'], item['sentiment'])
                    sentiment_distribution.append({
                        'sentiment': sentiment_es,
                        'count': item['count'],
                        'percentage': round((item['count'] / total_entries * 100) if total_entries > 0 else 0, 1)
                    })
            
            # Sentimiento más común
            most_common_sentiment = sentiment_distribution[0]['sentiment'] if sentiment_distribution else 'neutral'
            most_common_sentiment_percentage = sentiment_distribution[0]['percentage'] if sentiment_distribution else 0
            
            # Top 5 emociones
            emotion_counts = user_messages.values('dominant_emotion').annotate(
                count=Count('dominant_emotion')
            ).order_by('-count')[:5]
            
            top_emotions = []
            for item in emotion_counts:
                if item['dominant_emotion']:
                    emotion_es = EMOTION_MAPPING.get(item['dominant_emotion'], item['dominant_emotion'])
                    top_emotions.append({
                        'emotion': emotion_es,
                        'count': item['count']
                    })
            
            return Response({
                'total_users': 1,
                'total_entries': total_entries,
                'most_common_sentiment': most_common_sentiment,
                'most_common_sentiment_percentage': most_common_sentiment_percentage,
                'entries_last_week': entries_last_week,
                'sentiment_distribution': sentiment_distribution,
                'top_emotions': top_emotions,
                'users_stats': []
            }, status=status.HTTP_200_OK)
        
        elif user.is_teacher:
            # Estadísticas de estudiantes asignados
            assigned_students = user.students.all()
            
            if assigned_students.count() == 0:
                return Response({
                    'total_users': 0,
                    'total_entries': 0,
                    'most_common_sentiment': 'neutral',
                    'most_common_sentiment_percentage': 0,
                    'entries_last_week': 0,
                    'sentiment_distribution': [],
                    'top_emotions': [],
                    'users_stats': []
                }, status=status.HTTP_200_OK)
            
            # Obtener todas las conversaciones de los estudiantes asignados
            student_conversations = Conversation.objects.filter(user__in=assigned_students)
            all_student_messages = Message.objects.filter(
                conversation__in=student_conversations,
                sender='user'
            )
            
            total_entries = all_student_messages.count()
            
            # Mensajes de la última semana
            one_week_ago = timezone.now() - timedelta(days=7)
            entries_last_week = all_student_messages.filter(timestamp__gte=one_week_ago).count()
            
            # Distribución de sentimientos (agregada)
            sentiment_counts = all_student_messages.values('sentiment').annotate(
                count=Count('sentiment')
            ).order_by('-count')
            
            sentiment_distribution = []
            for item in sentiment_counts:
                if item['sentiment']:
                    sentiment_es = SENTIMENT_MAPPING.get(item['sentiment'], item['sentiment'])
                    sentiment_distribution.append({
                        'sentiment': sentiment_es,
                        'count': item['count'],
                        'percentage': round((item['count'] / total_entries * 100) if total_entries > 0 else 0, 1)
                    })
            
            # Sentimiento más común
            most_common_sentiment = sentiment_distribution[0]['sentiment'] if sentiment_distribution else 'neutral'
            most_common_sentiment_percentage = sentiment_distribution[0]['percentage'] if sentiment_distribution else 0
            
            # Top 5 emociones
            emotion_counts = all_student_messages.values('dominant_emotion').annotate(
                count=Count('dominant_emotion')
            ).order_by('-count')[:5]
            
            top_emotions = []
            for item in emotion_counts:
                if item['dominant_emotion']:
                    emotion_es = EMOTION_MAPPING.get(item['dominant_emotion'], item['dominant_emotion'])
                    top_emotions.append({
                        'emotion': emotion_es,
                        'count': item['count']
                    })
            
            # Estadísticas por estudiante individual
            users_stats = []
            for student in assigned_students:
                student_convs = Conversation.objects.filter(user=student)
                student_msgs = Message.objects.filter(
                    conversation__in=student_convs,
                    sender='user'
                )
                
                entries_count = student_msgs.count()
                
                # Sentimiento dominante del estudiante
                student_sentiment = student_msgs.values('sentiment').annotate(
                    count=Count('sentiment')
                ).order_by('-count').first()
                
                dominant_sentiment = student_sentiment['sentiment'] if student_sentiment and student_sentiment['sentiment'] else 'NEU'
                dominant_sentiment_es = SENTIMENT_MAPPING.get(dominant_sentiment, dominant_sentiment)
                
                # Emoción dominante del estudiante
                student_emotion = student_msgs.values('dominant_emotion').annotate(
                    count=Count('dominant_emotion')
                ).order_by('-count').first()
                
                dominant_emotion = student_emotion['dominant_emotion'] if student_emotion and student_emotion['dominant_emotion'] else 'others'
                dominant_emotion_es = EMOTION_MAPPING.get(dominant_emotion, dominant_emotion)
                
                users_stats.append({
                    'user_id': student.id,
                    'username': student.username,
                    'email': student.email,
                    'entries_count': entries_count,
                    'dominant_sentiment': dominant_sentiment_es,
                    'dominant_emotion': dominant_emotion_es
                })
            
            return Response({
                'total_users': assigned_students.count(),
                'total_entries': total_entries,
                'most_common_sentiment': most_common_sentiment,
                'most_common_sentiment_percentage': most_common_sentiment_percentage,
                'entries_last_week': entries_last_week,
                'sentiment_distribution': sentiment_distribution,
                'top_emotions': top_emotions,
                'users_stats': users_stats
            }, status=status.HTTP_200_OK)
        
        else:
            return Response({
                'error': 'Tipo de usuario no reconocido'
            }, status=status.HTTP_400_BAD_REQUEST)

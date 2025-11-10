from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Conversation, Message
from .serializers import ChatResponseSerializer, CourseEmotionRecommendationSerializer
from .emotion_analyzer import EmotionAnalyzer, EMOTION_MAPPING, SENTIMENT_MAPPING
from .course_recommendation_service import CourseEmotionRecommendationService
import google.generativeai as genai
import os
from django.db.models import Count
from datetime import timedelta, datetime
from django.utils import timezone
from django.http import HttpResponse, Http404
from users.models import Course

# Configurar Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Crear modelo Gemini 2.5 Flash
model = genai.GenerativeModel('gemini-2.5-flash')

# Crear analizador de emociones (Hugging Face API - pysentimiento)
emotion_analyzer = EmotionAnalyzer()

# Importar generador de recursos solo si está disponible
try:
    from .support_resources_generator import SupportResourcesGenerator
    support_generator = SupportResourcesGenerator()
    SUPPORT_ENABLED = True
except ImportError:
    print("[WARNING] SupportResourcesGenerator not available")
    SUPPORT_ENABLED = False

# Importar generador de PDF solo si está disponible
try:
    from .pdf_generator import PDFReportGenerator
    PDF_ENABLED = True
except ImportError:
    print("[WARNING] PDFReportGenerator not available - install reportlab and matplotlib")
    PDF_ENABLED = False

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
        """
        Retorna un tip educativo sobre la emoción detectada.
        Basado en:
        - "Educar con inteligencia emocional" (Daniel Goleman)
        - "La educación emocional" (Rafael Bisquerra)
        - Marco CASEL para el aprendizaje socioemocional
        - "El cerebro del niño" (Daniel J. Siegel & Tina Payne Bryson)
        """
        tips = {
            "alegría": (
                "La alegría activa neurotransmisores que fortalecen la memoria y el aprendizaje. "
                "Según Goleman, las emociones positivas amplían nuestra capacidad de pensar creativamente. "
                "Registra qué actividades o personas generan esta emoción para cultivarla intencionalmente."
            ),
            "tristeza": (
                "La tristeza es una emoción adaptativa que nos permite procesar pérdidas y reconectar con lo que valoramos. "
                "Bisquerra enfatiza que validar la tristeza, no suprimirla, es clave para el desarrollo emocional saludable. "
                "Permítete sentirla; es parte natural del ser humano y señal de que algo te importa profundamente."
            ),
            "enojo": (
                "El enojo nos alerta cuando nuestros límites o valores son transgredidos (Siegel & Bryson). "
                "No es 'mala' la emoción, sino lo que hacemos con ella. Pregúntate: ¿Qué necesidad o límite no está siendo respetado? "
                "Expresar el enojo asertivamente, sin dañar, es una competencia socioemocional esencial según CASEL."
            ),
            "miedo": (
                "El miedo prepara nuestro cuerpo para protegernos. Según la neurociencia del aprendizaje, identificar si el miedo es real o anticipado "
                "ayuda a regularlo. Pregúntate: ¿Qué evidencia tengo? ¿Qué es lo peor que podría pasar realmente? "
                "Esta reflexión activa tu córtex prefrontal, ayudándote a pensar con más claridad (Goleman)."
            ),
            "disgusto": (
                "El disgusto nos protege de situaciones, personas o comportamientos que percibimos como dañinos o inapropiados. "
                "Bisquerra señala que esta emoción nos ayuda a establecer límites saludables. "
                "Reflexiona: ¿Qué valores o principios míos están siendo vulnerados? ¿Qué límite debo comunicar?"
            ),
            "sorpresa": (
                "La sorpresa interrumpe nuestros esquemas mentales y nos prepara para nueva información. "
                "Según CASEL, esta emoción breve fomenta la curiosidad y el aprendizaje. "
                "Pregúntate: ¿Esta sorpresa abre oportunidades o representa un reto? Tu interpretación definirá tu respuesta emocional."
            ),
            "neutral": (
                "La ecuanimidad emocional es un estado valioso que facilita la toma de decisiones racionales (Goleman). "
                "No todas las situaciones requieren emociones intensas. Reconocer la calma interior como un estado positivo "
                "es parte de la inteligencia emocional según el marco de Bisquerra."
            ),
            "gratitud": (
                "La gratitud, según investigaciones de psicología positiva, mejora el bienestar, fortalece relaciones y aumenta la resiliencia. "
                "Expresar agradecimiento activa el sistema de recompensa cerebral. Como sugiere CASEL, "
                "mantener un diario de gratitud o expresarla a otros refuerza conexiones significativas."
            ),
            "orgullo": (
                "El orgullo sano reconoce tus esfuerzos y logros, fortaleciendo tu autoestima (Bisquerra). "
                "A diferencia del orgullo desmedido, celebrar tus avances fomenta la motivación intrínseca y la perseverancia. "
                "Reconoce tu trabajo: ¿Qué habilidades desarrollaste? ¿Qué obstáculos superaste?"
            ),
        }
        
        default_tip = (
            "Reconocer y nombrar tus emociones es el primer paso del autoconocimiento emocional (Goleman). "
            "La competencia de autoconciencia, según CASEL, permite comprender cómo tus emociones influyen en tu pensamiento y comportamiento. "
            "Cada emoción tiene un mensaje valioso si aprendes a escucharla."
        )
        
        return tips.get(emotion, default_tip)

    def _infer_emotion_from_text(self, text: str) -> str:
        """Heurística simple para inferir emoción cuando el modelo devuelve neutral."""
        t = (text or "").lower()
        if any(w in t for w in ["triste", "soledad", "solo", "llorar", "deprim"]):
            return "tristeza"
        if any(w in t for w in ["ansio", "miedo", "preocup", "nervios"]):
            return "miedo"
        if any(w in t for w in ["enojo", "rabia", "furia", "molest"]):
            return "enojo"
        if any(w in t for w in ["feliz", "content", "alegr", "gracia"]):
            return "alegría"
        return "neutral"

    def _get_micro_tip(self, emotion_es: str) -> str:
        """Devuelve una micro‑técnica breve y accionable; enfoque educativo, no terapéutico."""
        tips = {
            "tristeza": (
                "Micro‑técnica (3 pasos) para tristeza:\n"
                "1) Respiración 4‑7‑8: inhala 4s, sostén 7s, exhala 8s (x3).\n"
                "2) Grounding 5‑4‑3‑2‑1: 5 cosas que ves, 4 que tocas, 3 que oyes, 2 que hueles, 1 que saboreas.\n"
                "3) Diario: completa ‘Ahora mismo me siento… porque…’."
            ),
            "miedo": (
                "Micro‑técnica para ansiedad/miedo:\n"
                "1) Respiración cuadrada 4‑4‑4‑4 por 1 min.\n"
                "2) Pregunta lógica: ¿Qué evidencia real tengo? ¿Qué es lo más probable?\n"
                "3) Define un paso pequeño (5 min) que puedas hacer ahora."
            ),
            "enojo": (
                "Micro‑técnica para enojo:\n"
                "1) Pausa 60–90s lejos del estímulo.\n"
                "2) Nombra la necesidad: ‘Me enojo cuando… porque necesito…’.\n"
                "3) Canaliza: escribe o camina 5 min antes de responder."
            ),
            "alegría": (
                "Micro‑técnica para alegría:\n"
                "1) Regístrala: ¿qué la generó?\n"
                "2) Ancla corporal: 3 respiraciones notando dónde la sientes.\n"
                "3) Plan: cómo repetir esa condición esta semana."
            ),
            "neutral": (
                "Micro‑técnica general:\n"
                "1) Escaneo corporal de 1 minuto (cabeza a pies).\n"
                "2) Dos respiraciones profundas y lentas.\n"
                "3) Escribe una frase: ‘Lo más importante ahora es…’."
            ),
        }
        return tips.get(emotion_es, tips["neutral"]) + "\nNota: guía educativa; no reemplaza atención psicológica."

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

        # ===== ANÁLISIS HÍBRIDO: PYSENTIMIENTO + GOEMOTIONS =====
        print(f"\n[CHAT] Iniciando análisis híbrido del mensaje...")
        hf_analysis = emotion_analyzer.analyze_complete_hybrid(text)
        
        # Extraer resultados del análisis híbrido
        pysentimiento_emotion = hf_analysis['pysentimiento_emotion']
        pysentimiento_sentiment = hf_analysis['pysentimiento_sentiment']
        goemotions_primary = hf_analysis['goemotions_primary']
        goemotions_secondary = hf_analysis['goemotions_secondary']
        
        # Emoción primaria global (puede ser de pysentimiento o goemotions)
        primary_emotion = hf_analysis['primary_emotion']
        primary_emotion_source = hf_analysis['primary_emotion_source']
        intensity_level = hf_analysis['intensity']

        # Puntajes base de Pysentimiento
        emotion_scores = pysentimiento_emotion.get('emotions', {})

        # Fallback heurístico si Pysentimiento devolvió todos 0 y 'others':1.0
        try:
            non_others_sum = sum(v for k, v in emotion_scores.items() if k != 'others')
            others_val = emotion_scores.get('others', 0)
        except Exception:
            non_others_sum = 0
            others_val = 0

        if others_val >= 0.99 and non_others_sum == 0:
            guessed_es = self._infer_emotion_from_text(text)
            mapping_rev = {
                'tristeza': 'sadness',
                'miedo': 'fear',
                'enojo': 'anger',
                'alegría': 'joy',
                'alegria': 'joy',
            }
            guessed = mapping_rev.get(guessed_es, 'others')
            if guessed != 'others':
                print(f"[FALLBACK] Ajustando emoción a '{guessed}' por heurística de texto")
                emotion_scores = {
                    'joy': 0.0,
                    'sadness': 0.0,
                    'anger': 0.0,
                    'fear': 0.0,
                    'surprise': 0.0,
                    'disgust': 0.0,
                    'others': 0.1,
                }
                emotion_scores[guessed] = 0.9
                pysentimiento_emotion['emotions'] = emotion_scores
                pysentimiento_emotion['dominant_emotion'] = guessed
                pysentimiento_emotion['confidence'] = 0.6
                # Si la primaria venía como 'others', usa la inferida
                if primary_emotion == 'others' or not primary_emotion:
                    primary_emotion = guessed
                    primary_emotion_source = 'heuristic'

        # Para compatibilidad con el prompt (usar la emoción primaria global)
        emotion = primary_emotion
        
        sentiment = pysentimiento_sentiment['sentiment']
        sentiment_scores = pysentimiento_sentiment['scores']
        
        print(f"[CHAT] Análisis completado: Primaria={primary_emotion} ({primary_emotion_source}), Intensidad={intensity_level}")
        
        # ===== GUARDAR ANÁLISIS EN LA BASE DE DATOS =====
        # Pysentimiento (7 emociones)
        user_message.dominant_emotion = pysentimiento_emotion['dominant_emotion']
        user_message.emotion_joy_score = emotion_scores.get('joy', 0.0)
        user_message.emotion_sadness_score = emotion_scores.get('sadness', 0.0)
        user_message.emotion_anger_score = emotion_scores.get('anger', 0.0)
        user_message.emotion_fear_score = emotion_scores.get('fear', 0.0)
        user_message.emotion_disgust_score = emotion_scores.get('disgust', 0.0)
        user_message.emotion_surprise_score = emotion_scores.get('surprise', 0.0)
        user_message.emotion_others_score = emotion_scores.get('others', 0.0)
        
        # GoEmotions primarias (2 emociones)
        user_message.emotion_gratitude_score = goemotions_primary.get('gratitude', 0.0)
        user_message.emotion_pride_score = goemotions_primary.get('pride', 0.0)
        
        # GoEmotions secundarias (JSON)
        user_message.secondary_emotions = goemotions_secondary if goemotions_secondary else {}
        
        # Emoción primaria global
        user_message.primary_emotion = primary_emotion
        user_message.primary_emotion_source = primary_emotion_source
        
        # Actualizar sentimiento
        user_message.sentiment = sentiment
        user_message.sentiment_pos_score = sentiment_scores.get('POS', 0.0)
        user_message.sentiment_neg_score = sentiment_scores.get('NEG', 0.0)
        user_message.sentiment_neu_score = sentiment_scores.get('NEU', 0.0)
        
        user_message.save()
        print(f"Análisis guardado en base de datos")

        # Traducir resultados a español
        dominant_emotion_es = EMOTION_MAPPING.get(emotion, emotion)
        dominant_sentiment_es = SENTIMENT_MAPPING.get(sentiment, sentiment)

        # ===== GENERAR RESPUESTA EMPÁTICA CON GEMINI =====
        print(f"Generando respuesta con Gemini...")
        prompt = self._build_context_prompt(
            conversation=conversation,
            current_text=text,
            emotion_es=dominant_emotion_es,
            sentiment_es=dominant_sentiment_es
        )
        
        bot_text = self._generate_gemini_response(prompt)
        print(f"Respuesta generada")
        
        # Guardar respuesta del bot
        Message.objects.create(
            conversation=conversation,
            text=bot_text,
            sender='bot'
        )

        # ===== VERIFICAR SI SE NECESITAN RECURSOS DE APOYO =====
        support_resources_data = None
        if SUPPORT_ENABLED and support_generator.requires_support(hf_analysis):
            print(f"[SUPPORT] Se detectaron emociones negativas intensas, generando recursos...")
            
            try:
                # Generar recursos con IA
                support_resources_raw = support_generator.generate_support_resources(
                    text=text,
                    emotion=EMOTION_MAPPING.get(primary_emotion, primary_emotion),
                    intensity=intensity_level,
                    sentiment=SENTIMENT_MAPPING.get(sentiment, sentiment)
                )
                
                # Formatear para respuesta
                support_resources_data = support_generator.format_resources_for_response(support_resources_raw)
                
                # Guardar en el mensaje del usuario
                user_message.support_resources_offered = True
                user_message.support_resources = support_resources_raw
                user_message.save()
                
                print(f"[SUPPORT] Recursos generados y guardados")
            except Exception as e:
                print(f"[SUPPORT] Error generando recursos: {e}")
        
        # ===== PREPARAR RESPUESTA PARA EL FRONTEND =====
        # Traducir emoción primaria global
        primary_emotion_es = EMOTION_MAPPING.get(primary_emotion, primary_emotion)
        dominant_sentiment_es = SENTIMENT_MAPPING.get(sentiment, sentiment)
        # Si el modelo devolvió neutral, inferir por texto para entregar un tip útil
        emotion_for_tip = primary_emotion_es if primary_emotion_es != 'neutral' else self._infer_emotion_from_text(text)

        # Mostrar tip solo si la confianza de alguna emoción es alta (>= 0.85)
        TIP_THRESHOLD = 0.85
        pysen_max = 0.0
        try:
            pysen_max = max(emotion_scores.values()) if isinstance(emotion_scores, dict) and emotion_scores else 0.0
        except Exception:
            pysen_max = 0.0
        go_max = 0.0
        try:
            go_max = max(goemotions_primary.values()) if isinstance(goemotions_primary, dict) and goemotions_primary else 0.0
        except Exception:
            go_max = 0.0
        show_tip = max(pysen_max, go_max) >= TIP_THRESHOLD
        educational_tip_value = self._get_micro_tip(emotion_for_tip) if show_tip else ""
        
        # Emociones secundarias de GoEmotions (>=10%, ordenadas desc)
        secondary_emotions_list = []
        try:
            MIN_SEC_THRESHOLD = 0.10  # 10%
            secondary_sorted = sorted(
                (goemotions_secondary or {}).items(),
                key=lambda x: x[1],
                reverse=True
            )
            for label, score in secondary_sorted:
                if score and score >= MIN_SEC_THRESHOLD:
                    secondary_emotions_list.append({
                        'emotion': EMOTION_MAPPING.get(label, label),
                        'score': round(score * 100, 1)  # porcentaje
                    })
        except Exception:
            secondary_emotions_list = []
        
        response_data = {
            "bot_response": bot_text,
            "conversation_id": conversation.id,
            "emotional_insight": {
                "primary_emotion": primary_emotion_es,
                "primary_emotion_source": primary_emotion_source,
                "intensity": intensity_level,
                "educational_tip": educational_tip_value,
                "secondary_emotions_detected": secondary_emotions_list
            },
            "support_resources": support_resources_data,  # Recursos de apoyo si aplica
            "user_message_analysis": {
                "text": text,
                "sentiment": {
                    "dominant": dominant_sentiment_es,
                    "Positivo": round(sentiment_scores.get('POS', 0) * 100, 1),
                    "Negativo": round(sentiment_scores.get('NEG', 0) * 100, 1),
                    "Neutral": round(sentiment_scores.get('NEU', 0) * 100, 1),
                },
                "emotions_primary": {
                    "source": "pysentimiento",
                    "dominant": EMOTION_MAPPING.get(pysentimiento_emotion['dominant_emotion'], pysentimiento_emotion['dominant_emotion']),
                    "Alegria": round(emotion_scores.get('joy', 0) * 100, 1),
                    "Tristeza": round(emotion_scores.get('sadness', 0) * 100, 1),
                    "Enojo": round(emotion_scores.get('anger', 0) * 100, 1),
                    "Miedo": round(emotion_scores.get('fear', 0) * 100, 1),
                    "Disgusto": round(emotion_scores.get('disgust', 0) * 100, 1),
                    "Sorpresa": round(emotion_scores.get('surprise', 0) * 100, 1),
                    "Otros": round(emotion_scores.get('others', 0) * 100, 1),
                },
                "emotions_goemotions_primary": {
                    "Gratitud": round(goemotions_primary.get('gratitude', 0) * 100, 1),
                    "Orgullo": round(goemotions_primary.get('pride', 0) * 100, 1),
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


class ExportDashboardPDFView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        Endpoint para exportar el dashboard a PDF.
        Solo disponible para profesores.
        """
        if not PDF_ENABLED:
            return Response({
                'error': 'La exportación PDF no está disponible. Instalar reportlab y matplotlib'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        user = request.user
        
        # Verificar que sea profesor
        if not user.is_teacher:
            return Response({
                'error': 'Solo los profesores pueden exportar reportes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Obtener estadísticas (reutilizando lógica de DashboardStatsView)
        assigned_students = user.students.all()
        
        if assigned_students.count() == 0:
            return Response({
                'error': 'No tienes estudiantes asignados para generar el reporte'
            }, status=status.HTTP_400_BAD_REQUEST)
        
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
        
        # Estadísticas por estudiante individual (ANÓNIMO para PDF)
        users_stats = []
        for idx, student in enumerate(assigned_students, start=1):
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
                # Mantener anonimato: no incluir username ni email
                'display_name': f'Estudiante #{idx}',
                'entries_count': entries_count,
                'dominant_sentiment': dominant_sentiment_es,
                'dominant_emotion': dominant_emotion_es
            })
        
        # Preparar datos para el PDF
        stats_data = {
            'total_users': assigned_students.count(),
            'total_entries': total_entries,
            'most_common_sentiment': most_common_sentiment,
            'most_common_sentiment_percentage': most_common_sentiment_percentage,
            'entries_last_week': entries_last_week,
            'sentiment_distribution': sentiment_distribution,
            'top_emotions': top_emotions,
            'users_stats': users_stats
        }
        
        # Generar PDF
        try:
            print("[PDF] Generando reporte...")
            pdf_generator = PDFReportGenerator(user, stats_data)
            pdf_bytes = pdf_generator.generate()
            print("[PDF] Reporte generado exitosamente")
            
            # Nombre del archivo
            filename = f"reporte_emocional_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            
            # Crear respuesta HTTP con el PDF
            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            print(f"[PDF] Error generando PDF: {e}")
            return Response({
                'error': f'Error al generar el PDF: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseEmotionRecommendationView(APIView):
    """
    Permite a profesores y administradores solicitar y consultar recomendaciones socioemocionales
    generadas por IA para un curso específico.
    """

    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recommendation_service = CourseEmotionRecommendationService()

    def get(self, request, course_id):
        course = self._get_course(course_id)
        self._ensure_access(request.user, course)

        limit = request.query_params.get('limit')
        queryset = course.emotion_recommendations.all()
        if limit:
            try:
                limit_value = max(1, min(int(limit), 20))
                queryset = queryset[:limit_value]
            except ValueError:
                pass

        serializer = CourseEmotionRecommendationSerializer(queryset, many=True)
        return Response({
            'course': {
                'id': course.id,
                'name': course.name,
                'code': course.code,
            },
            'results': serializer.data,
        }, status=status.HTTP_200_OK)

    def post(self, request, course_id):
        course = self._get_course(course_id)
        self._ensure_access(request.user, course)

        try:
            recommendation = self.recommendation_service.generate_recommendation(course, request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = CourseEmotionRecommendationSerializer(recommendation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_course(self, course_id):
        try:
            return Course.objects.get(pk=course_id)
        except Course.DoesNotExist as exc:
            raise Http404("Curso no encontrado") from exc

    def _ensure_access(self, user, course: Course):
        if user.is_admin:
            return
        if user.is_teacher and course.teacher_id == user.id:
            return
        raise PermissionDenied("Solo el profesor asignado o un administrador pueden consultar estas recomendaciones.")

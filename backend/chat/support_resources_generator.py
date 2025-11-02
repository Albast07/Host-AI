# backend/chat/support_resources_generator.py

import google.generativeai as genai
import os
import json
from datetime import datetime

# Configurar Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.5-flash')


class SupportResourcesGenerator:
    """
    Generador de recursos de apoyo emocional usando IA.
    Cuando detecta emociones negativas intensas, genera sugerencias contextuales.
    """
    
    # Umbrales para activar recursos de ayuda
    INTENSITY_THRESHOLDS = {
        'high': 0.7,
        'medium': 0.5
    }
    
    NEGATIVE_EMOTIONS = ['sadness', 'fear', 'anger', 'disgust']
    
    def __init__(self):
        self.model = model
    
    def requires_support(self, analysis):
        """
        Determina si el mensaje requiere ofrecer recursos de apoyo.
        
        Args:
            analysis: Diccionario con análisis emocional completo
            
        Returns:
            bool: True si se deben ofrecer recursos
        """
        primary_emotion = analysis.get('primary_emotion', '')
        intensity = analysis.get('intensity', 'low')
        sentiment_scores = analysis['pysentimiento_sentiment']['scores']
        
        # Criterio 1: Emoción negativa con intensidad alta
        if primary_emotion in self.NEGATIVE_EMOTIONS and intensity == 'high':
            return True
        
        # Criterio 2: Emoción negativa con intensidad media + sentimiento muy negativo
        if primary_emotion in self.NEGATIVE_EMOTIONS and intensity == 'medium':
            if sentiment_scores.get('NEG', 0) > 0.6:
                return True
        
        # Criterio 3: Sentimiento extremadamente negativo (>70%)
        if sentiment_scores.get('NEG', 0) > 0.7:
            return True
        
        return False
    
    def analyze_recent_pattern(self, recent_messages):
        """
        Analiza los últimos mensajes para detectar patrones negativos persistentes.
        
        Args:
            recent_messages: Lista de objetos Message (últimos 5)
            
        Returns:
            dict: Información sobre patrones detectados
        """
        if not recent_messages:
            return {'consecutive_negative': 0, 'pattern_detected': False}
        
        negative_count = 0
        for msg in recent_messages[:5]:  # Últimos 5 mensajes
            if msg.sentiment in ['NEG', 'negative', 'negativo']:
                negative_count += 1
        
        pattern_detected = negative_count >= 3
        
        return {
            'consecutive_negative': negative_count,
            'pattern_detected': pattern_detected,
            'total_analyzed': len(recent_messages)
        }
    
    def generate_support_resources(self, text, emotion, intensity, sentiment):
        """
        Genera recursos de apoyo contextuales usando IA (Gemini).
        
        Args:
            text: Mensaje del usuario
            emotion: Emoción detectada (en español)
            intensity: Intensidad (low/medium/high)
            sentiment: Sentimiento (positivo/negativo/neutral)
            
        Returns:
            dict: Recursos generados con técnicas y mensaje de apoyo
        """
        
        prompt = f"""Eres un asistente educativo de inteligencia emocional para estudiantes de 12 a 18 años.

SITUACIÓN DETECTADA:
- Mensaje del estudiante: "{text}"
- Emoción identificada: {emotion}
- Intensidad: {intensity}
- Sentimiento general: {sentiment}

TAREA:
Genera recursos de apoyo emocional apropiados en formato JSON. Debes proporcionar:

1. **techniques**: Lista de 2-3 técnicas prácticas (cada una con título y pasos)
2. **supportive_message**: Un mensaje empático y de apoyo (2-3 oraciones máximo)
3. **educational_insight**: Una breve explicación educativa sobre la emoción (1-2 oraciones)

TIPOS DE TÉCNICAS A SUGERIR:
- **Respiración**: Ejercicios de respiración consciente (ej: 4-7-8, respiración cuadrada)
- **Grounding**: Técnicas de anclaje al presente (ej: 5-4-3-2-1, observación consciente)
- **Journaling**: Escritura reflexiva o expresiva
- **Movimiento**: Actividad física suave (caminar, estiramiento)
- **Contacto**: Hablar con alguien de confianza

IMPORTANTE:
- Usa lenguaje cercano para adolescentes (sin ser condescendiente)
- Sé breve y práctico
- Todas las emociones son válidas
- No des terapia, solo educación emocional
- No minimices lo que sienten
- Enfócate en dar herramientas, no soluciones

FORMATO DE SALIDA (JSON estricto, sin comentarios):
{{
  "techniques": [
    {{
      "type": "breathing|grounding|journaling|movement|contact",
      "title": "Título corto",
      "steps": [
        "Paso 1",
        "Paso 2",
        "Paso 3"
      ],
      "duration": "1-2 minutos|5 minutos|10 minutos"
    }}
  ],
  "supportive_message": "Mensaje empático validando la emoción",
  "educational_insight": "Breve explicación educativa sobre la emoción"
}}

GENERA SOLO EL JSON, SIN TEXTO ADICIONAL:"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Limpiar respuesta (remover markdown si existe)
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            resources = json.loads(response_text)
            
            # Validar estructura básica
            if 'techniques' not in resources or 'supportive_message' not in resources:
                raise ValueError("Respuesta incompleta de la IA")
            
            # Agregar metadata
            resources['generated_at'] = datetime.now().isoformat()
            resources['emotion_context'] = {
                'emotion': emotion,
                'intensity': intensity,
                'sentiment': sentiment
            }
            
            return resources
            
        except Exception as e:
            print(f"Error generando recursos con IA: {e}")
            # Fallback: recursos predefinidos básicos
            return self._get_fallback_resources(emotion, intensity)
    
    def _get_fallback_resources(self, emotion, intensity):
        """
        Recursos predefinidos de respaldo si la IA falla.
        """
        fallback = {
            'techniques': [
                {
                    'type': 'breathing',
                    'title': 'Respiración 4-7-8',
                    'steps': [
                        'Inhala profundamente por la nariz contando hasta 4',
                        'Sostén la respiración contando hasta 7',
                        'Exhala completamente por la boca contando hasta 8',
                        'Repite 3-4 veces'
                    ],
                    'duration': '2-3 minutos'
                },
                {
                    'type': 'grounding',
                    'title': 'Técnica 5-4-3-2-1',
                    'steps': [
                        'Nombra 5 cosas que puedes VER',
                        'Nombra 4 cosas que puedes TOCAR',
                        'Nombra 3 cosas que puedes ESCUCHAR',
                        'Nombra 2 cosas que puedes OLER',
                        'Nombra 1 cosa que puedes SABOREAR'
                    ],
                    'duration': '3-5 minutos'
                }
            ],
            'supportive_message': f'Noté que estás experimentando {emotion}. Es completamente válido sentir esto. Estas técnicas pueden ayudarte a manejar lo que sientes en este momento.',
            'educational_insight': f'La {emotion} es una emoción natural que nos ayuda a procesar situaciones difíciles. Reconocerla es el primer paso.',
            'generated_at': datetime.now().isoformat(),
            'emotion_context': {
                'emotion': emotion,
                'intensity': intensity,
                'sentiment': 'negativo'
            },
            'is_fallback': True
        }
        
        return fallback
    
    def format_resources_for_response(self, resources):
        """
        Formatea los recursos para la respuesta del API.
        
        Args:
            resources: Diccionario de recursos generados
            
        Returns:
            dict: Recursos formateados para el frontend
        """
        return {
            'available': True,
            'message': resources.get('supportive_message', ''),
            'educational_insight': resources.get('educational_insight', ''),
            'techniques': resources.get('techniques', []),
            'generated_at': resources.get('generated_at'),
            'context': resources.get('emotion_context', {})
        }

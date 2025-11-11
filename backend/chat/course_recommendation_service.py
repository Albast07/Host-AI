"""
Servicio para generar recomendaciones pedagógicas basadas en la dinámica emocional de un curso.
Las sugerencias se inspiran en literatura de educación emocional (Bisquerra, Goleman, Siegel y CASEL)
y se apoyan en Gemini cuando está disponible. Siempre se aclara que no reemplazan a un profesional.
"""
from __future__ import annotations

import json
import os
from datetime import timedelta
from typing import Dict, List, Optional

import google.generativeai as genai
from django.db.models import Count
from django.utils import timezone

from .models import CourseEmotionRecommendation, Message
from users.models import Course

GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
DISCLAIMER_TEXT = (
    "Estas sugerencias se basan en educación socioemocional (Bisquerra, CASEL, Goleman) y "
    "no reemplazan el acompañamiento de psicología o psicopedagogía profesional."
)


class CourseEmotionRecommendationService:
    """
    Orquesta la agregación de emociones por curso y la generación de sugerencias contextuales.
    """

    TIME_WINDOW_DAYS = 7
    MIN_MESSAGES = 10
    ALERT_THRESHOLDS = {
        'sadness': 0.5,
        'fear': 0.45,
        'anger': 0.45,
    }

    LITERATURE_REFERENCES = {
        'sadness': "R. Bisquerra – 'La educación emocional' (gestión de la tristeza en el aula)",
        'fear': "D. J. Siegel – 'El cerebro del niño' (ventana de tolerancia y seguridad)",
        'anger': "CASEL Framework – habilidades socioemocionales para canalizar el enojo",
        'disgust': "Daniel Goleman – 'Inteligencia emocional' (autoconciencia y límites)",
        'surprise': "CASEL – curiosidad y mentalidad de crecimiento",
        'joy': "Barbara Fredrickson – teoría broaden-and-build sobre emociones positivas",
    }

    def __init__(self) -> None:
        api_key = os.getenv('GEMINI_API_KEY')
        self.model = None
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(GEMINI_MODEL)
            except Exception as exc:  # pragma: no cover - falla solo si credenciales son inválidas
                print(f"[CourseRecommendationService] No se pudo inicializar Gemini: {exc}")

    # ----------------------------------------------------------------------
    # Métricas base
    # ----------------------------------------------------------------------
    def collect_stats(self, course: Course) -> Dict:
        students_ids = list(course.students.values_list('id', flat=True))
        if not students_ids:
            return {
                'time_window_days': self.TIME_WINDOW_DAYS,
                'total_messages': 0,
                'emotion_counts': {},
                'emotion_ratios': {},
                'sentiment_counts': {},
                'recent_samples': [],
            }

        window_start = timezone.now() - timedelta(days=self.TIME_WINDOW_DAYS)
        qs = (
            Message.objects.filter(
                conversation__user_id__in=students_ids,
                sender='user',
                timestamp__gte=window_start,
            )
            .exclude(primary_emotion__isnull=True)
        )

        total = qs.count()
        emotion_counts = {
            row['primary_emotion']: row['total']
            for row in qs.values('primary_emotion').annotate(total=Count('id'))
        }
        sentiment_counts = {
            row['sentiment']: row['total']
            for row in qs.exclude(sentiment__isnull=True)
                           .values('sentiment').annotate(total=Count('id'))
        }

        emotion_ratios = {
            emotion: round(count / total, 3) if total else 0.0
            for emotion, count in emotion_counts.items()
        }

        recent_samples = list(
            qs.order_by('-timestamp')
              .values('text', 'primary_emotion', 'sentiment')[:5]
        )

        return {
            'time_window_days': self.TIME_WINDOW_DAYS,
            'total_messages': total,
            'emotion_counts': emotion_counts,
            'emotion_ratios': emotion_ratios,
            'sentiment_counts': sentiment_counts,
            'recent_samples': recent_samples,
        }

    # ----------------------------------------------------------------------
    # Generación de recomendaciones
    # ----------------------------------------------------------------------
    def generate_recommendation(
        self,
        course: Course,
        requested_by,
    ) -> CourseEmotionRecommendation:
        stats = self.collect_stats(course)
        if stats['total_messages'] < self.MIN_MESSAGES:
            raise ValueError(
                f"Se requieren al menos {self.MIN_MESSAGES} mensajes del curso en los últimos "
                f"{self.TIME_WINDOW_DAYS} días para generar una recomendación."
            )

        trigger = self._determine_trigger(stats)
        if not trigger:
            raise ValueError("No se detectaron patrones emocionales significativos en el periodo analizado.")

        content = self._build_content(course, trigger, stats)

        recommendation = CourseEmotionRecommendation.objects.create(
            course=course,
            generated_by=requested_by,
            triggered_emotion=trigger['emotion'],
            emotion_ratio=trigger['ratio'],
            time_window_days=self.TIME_WINDOW_DAYS,
            stats_snapshot=stats,
            overview=content['overview'],
            suggestions=content['suggestions'],
            disclaimer=DISCLAIMER_TEXT,
        )
        return recommendation

    def _determine_trigger(self, stats: Dict) -> Optional[Dict]:
        ratios = stats.get('emotion_ratios', {})
        for emotion, threshold in self.ALERT_THRESHOLDS.items():
            ratio = ratios.get(emotion, 0)
            if ratio >= threshold:
                return {'emotion': emotion, 'ratio': ratio, 'reason': 'threshold'}

        if not ratios:
            return None

        emotion, ratio = max(ratios.items(), key=lambda item: item[1])
        if ratio == 0:
            return None
        return {'emotion': emotion, 'ratio': ratio, 'reason': 'dominant'}

    def _build_content(self, course: Course, trigger: Dict, stats: Dict) -> Dict:
        if self.model:
            try:
                response = self.model.generate_content(self._build_prompt(course, trigger, stats))
                parsed = self._parse_ai_response(response.text)
                if parsed:
                    return parsed
            except Exception as exc:  # pragma: no cover - depende de red/servicio externo
                print(f"[CourseRecommendationService] Error al generar con Gemini: {exc}")

        return self._fallback_content(trigger)

    # ----------------------------------------------------------------------
    # Gemini helpers
    # ----------------------------------------------------------------------
    def _build_prompt(self, course: Course, trigger: Dict, stats: Dict) -> str:
        emotion = trigger['emotion']
        ratio = round(trigger['ratio'] * 100, 1)
        sample_texts = "\n".join(
            f"- \"{sample['text'][:160]}\" (emoción: {sample['primary_emotion']})"
            for sample in stats.get('recent_samples', [])
        ) or "- Sin ejemplos recientes disponibles"

        reference = self.LITERATURE_REFERENCES.get(
            emotion,
            "Referencias generales: Bisquerra, Goleman, CASEL, Siegel.",
        )

        return f"""
Eres un orientador pedagógico especializado en educación socioemocional.
Necesitas sugerir acciones para el curso "{course.name}" (código {course.code}).

Datos disponibles (últimos {stats['time_window_days']} días):
- Total de mensajes analizados: {stats['total_messages']}
- Emoción predominante: {emotion} ({ratio}% de los mensajes del alumnado)
- Recuento de emociones: {stats['emotion_counts']}
- Recuento de sentimientos: {stats['sentiment_counts']}
- Ejemplos recientes:
{sample_texts}

Considera siempre:
- Son recomendaciones educativas inspiradas en {reference}.
- Nunca reemplazan a profesionales de psicología o psicopedagogía.
- Propón actividades factibles dentro del aula o tutorías breves (10-20 min).
- Incluye al menos una acción colectiva y otra individual/reflexiva.

Formatea tu respuesta como JSON estricto con esta estructura:
{{
  "overview": "Resumen breve de lo que ocurre y objetivo pedagógico",
  "suggestions": [
    {{
      "title": "Título breve",
      "description": "¿Por qué ayuda esta estrategia?",
      "activity": "Actividad concreta (pasos resumidos)",
      "reference": "Libro o autor que respalda la sugerencia"
    }}
  ],
  "disclaimer": "{DISCLAIMER_TEXT}"
}}
Incluye entre 2 y 3 sugerencias.
"""

    def _parse_ai_response(self, text: str) -> Optional[Dict]:
        cleaned = text.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.strip('`')
            cleaned = cleaned.replace('json', '', 1).strip()

        try:
            payload = json.loads(cleaned)
            if 'overview' in payload and 'suggestions' in payload:
                if 'disclaimer' not in payload:
                    payload['disclaimer'] = DISCLAIMER_TEXT
                return payload
        except json.JSONDecodeError:
            return None
        return None

    # ----------------------------------------------------------------------
    # Fallback content
    # ----------------------------------------------------------------------
    def _fallback_content(self, trigger: Dict) -> Dict:
        emotion = trigger['emotion']
        reference = self.LITERATURE_REFERENCES.get(
            emotion,
            "R. Bisquerra – educación emocional",
        )

        suggestions = [
            {
                "title": "Rueda de emociones guiada",
                "description": (
                    "El profesor dedica 10 minutos a nombrar lo que sienten, validando cada emoción "
                    "y recordando que expresarla es seguro. Esta dinámica se inspira en Bisquerra."
                ),
                "activity": "Formar un círculo, compartir cómo se sienten usando tarjetas y sugerir estrategias de autocuidado.",
                "reference": reference,
            },
            {
                "title": "Bitácora de resiliencia",
                "description": (
                    "Invita a escribir tres ideas para cuidarse o pedir ayuda. Refuerza la idea de apoyo mutuo."
                ),
                "activity": "5 minutos de escritura individual y luego compartir voluntariamente recursos que ayudan.",
                "reference": "D. Goleman – 'Inteligencia emocional'.",
            },
        ]

        return {
            "overview": (
                f"Se detectó una presencia destacada de {emotion}. Se sugieren espacios breves para validar la emoción "
                "y actividades que fortalezcan la conexión grupal."
            ),
            "suggestions": suggestions,
            "disclaimer": DISCLAIMER_TEXT,
        }

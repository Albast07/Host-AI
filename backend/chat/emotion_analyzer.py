import requests
import os
from typing import Dict, List
import json


class EmotionAnalyzer:
    """
    Analizador de emociones usando pysentimiento desde Hugging Face API
    """
    
    def __init__(self):
        self.api_token = os.getenv('HUGGINGFACE_API_TOKEN')
        self.emotion_model_url = "https://api-inference.huggingface.co/models/finiteautomata/beto-emotion-analysis"
        self.sentiment_model_url = "https://api-inference.huggingface.co/models/finiteautomata/beto-sentiment-analysis"
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
    
    def analyze_emotion(self, text: str) -> Dict:
        """
        Analiza las emociones en el texto
        Retorna: {
            'dominant_emotion': str,
            'emotions': dict con scores de cada emoción
        }
        """
        try:
            response = requests.post(
                self.emotion_model_url,
                headers=self.headers,
                json={"inputs": text},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                
                # Procesar resultados
                if isinstance(results, list) and len(results) > 0:
                    emotions = results[0]
                    
                    # Ordenar por score
                    sorted_emotions = sorted(emotions, key=lambda x: x['score'], reverse=True)
                    
                    # Extraer emoción dominante
                    dominant_emotion = sorted_emotions[0]['label']
                    
                    # Crear dict con todas las emociones
                    emotion_scores = {
                        emotion['label']: round(emotion['score'], 4) 
                        for emotion in emotions
                    }
                    
                    return {
                        'dominant_emotion': dominant_emotion,
                        'emotions': emotion_scores,
                        'confidence': round(sorted_emotions[0]['score'], 4)
                    }
            
            # Si falla, retornar valores por defecto
            return self._default_emotion_response()
            
        except Exception as e:
            print(f"Error en análisis de emociones: {str(e)}")
            return self._default_emotion_response()
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analiza el sentimiento en el texto
        Retorna: {
            'sentiment': 'POS' | 'NEG' | 'NEU',
            'scores': dict con scores
        }
        """
        try:
            response = requests.post(
                self.sentiment_model_url,
                headers=self.headers,
                json={"inputs": text},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                
                if isinstance(results, list) and len(results) > 0:
                    sentiments = results[0]
                    sorted_sentiments = sorted(sentiments, key=lambda x: x['score'], reverse=True)
                    
                    dominant_sentiment = sorted_sentiments[0]['label']
                    
                    sentiment_scores = {
                        sent['label']: round(sent['score'], 4)
                        for sent in sentiments
                    }
                    
                    return {
                        'sentiment': dominant_sentiment,
                        'scores': sentiment_scores,
                        'confidence': round(sorted_sentiments[0]['score'], 4)
                    }
            
            return self._default_sentiment_response()
            
        except Exception as e:
            print(f"Error en análisis de sentimiento: {str(e)}")
            return self._default_sentiment_response()
    
    def analyze_complete(self, text: str) -> Dict:
        """
        Análisis completo: emociones + sentimiento
        """
        emotion_result = self.analyze_emotion(text)
        sentiment_result = self.analyze_sentiment(text)
        
        return {
            'text': text,
            'emotion_analysis': emotion_result,
            'sentiment_analysis': sentiment_result,
            'intensity': self._calculate_intensity(
                emotion_result.get('confidence', 0),
                sentiment_result.get('confidence', 0)
            )
        }
    
    def _calculate_intensity(self, emotion_conf: float, sentiment_conf: float) -> str:
        """
        Calcula la intensidad emocional basada en los scores
        """
        avg_confidence = (emotion_conf + sentiment_conf) / 2
        
        if avg_confidence >= 0.7:
            return "alta"
        elif avg_confidence >= 0.4:
            return "media"
        else:
            return "baja"
    
    def _default_emotion_response(self) -> Dict:
        """Respuesta por defecto cuando el análisis falla"""
        return {
            'dominant_emotion': 'neutral',
            'emotions': {
                'joy': 0.0,
                'sadness': 0.0,
                'anger': 0.0,
                'fear': 0.0,
                'surprise': 0.0,
                'others': 1.0
            },
            'confidence': 0.0
        }
    
    def _default_sentiment_response(self) -> Dict:
        """Respuesta por defecto cuando el análisis falla"""
        return {
            'sentiment': 'NEU',
            'scores': {
                'POS': 0.0,
                'NEG': 0.0,
                'NEU': 1.0
            },
            'confidence': 0.0
        }


# Mapeo de emociones a español
EMOTION_MAPPING = {
    'joy': 'alegría',
    'sadness': 'tristeza',
    'anger': 'enojo',
    'fear': 'miedo',
    'surprise': 'sorpresa',
    'others': 'neutral'
}

# Mapeo de sentimientos a español
SENTIMENT_MAPPING = {
    'POS': 'positivo',
    'NEG': 'negativo',
    'NEU': 'neutral'
}

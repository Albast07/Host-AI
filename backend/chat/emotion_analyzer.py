import requests
import os
from typing import Dict, List
import json


class EmotionAnalyzer:
    """
    Analizador de emociones HÍBRIDO:
    - pysentimiento: Análisis principal (español, 7 emociones)
    - GoEmotions: Análisis complementario (inglés, 27 emociones)
    """
    
    # Emociones primarias de GoEmotions que destacamos
    GOEMOTIONS_PRIMARY = ['gratitude', 'pride']
    
    # Emociones secundarias de GoEmotions
    GOEMOTIONS_SECONDARY = [
        'admiration', 'amusement', 'approval', 'caring', 'confusion',
        'curiosity', 'desire', 'disappointment', 'disapproval', 
        'embarrassment', 'excitement', 'grief', 'love', 'nervousness',
        'optimism', 'relief', 'remorse', 'neutral', 'realization'
    ]
    
    def __init__(self):
        self.api_token = os.getenv('HUGGINGFACE_API_TOKEN')
        if not self.api_token:
            print("WARNING: HUGGINGFACE_API_TOKEN no configurado")
        
        # URLs de modelos
        self.emotion_model_url = "https://api-inference.huggingface.co/models/finiteautomata/beto-emotion-analysis"
        self.sentiment_model_url = "https://api-inference.huggingface.co/models/finiteautomata/beto-sentiment-analysis"
        self.goemotions_model_url = "https://api-inference.huggingface.co/models/SamLowe/roberta-base-go_emotions"
        
        self.headers = {"Authorization": f"Bearer {self.api_token}"}
    
    def _translate_to_english(self, text: str) -> str:
        """
        Traduce texto al inglés para GoEmotions
        Usa Google Translate vía googletrans
        """
        try:
            from googletrans import Translator
            translator = Translator()
            translated = translator.translate(text, src='es', dest='en')
            print(f"[Traducción] ES: '{text[:50]}...' → EN: '{translated.text[:50]}...'")
            return translated.text
        except ImportError:
            print("[ERROR] googletrans no instalado. Ejecuta: pip install googletrans==4.0.0-rc1")
            return text
        except Exception as e:
            print(f"[ERROR] Traducción falló: {e}. Usando texto original.")
            return text
    
    def analyze_goemotions(self, text: str, retry=2) -> Dict:
        """
        Analiza emociones con GoEmotions (27 emociones en inglés)
        """
        try:
            # Traducir a inglés
            text_en = self._translate_to_english(text)
            
            for attempt in range(retry):
                try:
                    response = requests.post(
                        self.goemotions_model_url,
                        headers=self.headers,
                        json={"inputs": text_en},
                        timeout=15
                    )
                    
                    # Modelo cargándose
                    if response.status_code == 503:
                        print(f"[GoEmotions] Modelo cargándose, reintento {attempt + 1}/{retry}")
                        if attempt < retry - 1:
                            import time
                            time.sleep(3)
                            continue
                        else:
                            print("[GoEmotions] Modelo no disponible, usando valores por defecto")
                            return self._default_goemotions_response()
                    
                    if response.status_code == 200:
                        results = response.json()
                        
                        if isinstance(results, list) and len(results) > 0:
                            emotions = results[0]
                            
                            # Separar emociones primarias y secundarias
                            primary_emotions = {}
                            secondary_emotions = {}
                            
                            for emotion in emotions:
                                label = emotion['label']
                                score = round(emotion['score'], 4)
                                
                                if label in self.GOEMOTIONS_PRIMARY:
                                    primary_emotions[label] = score
                                elif label in self.GOEMOTIONS_SECONDARY:
                                    secondary_emotions[label] = score
                            
                            # Encontrar emoción dominante de las primarias
                            dominant_primary = None
                            if primary_emotions:
                                dominant_primary = max(primary_emotions.items(), key=lambda x: x[1])
                            
                            print(f"[GoEmotions] Análisis exitoso. Primarias: {list(primary_emotions.keys())}, Secundarias: {len(secondary_emotions)}")
                            
                            return {
                                'primary_emotions': primary_emotions,
                                'secondary_emotions': secondary_emotions,
                                'dominant_primary': dominant_primary,
                                'all_emotions': {e['label']: round(e['score'], 4) for e in emotions}
                            }
                    
                    print(f"[GoEmotions] Error {response.status_code}: {response.text[:100]}")
                    
                except requests.exceptions.Timeout:
                    print(f"[GoEmotions] Timeout en intento {attempt + 1}/{retry}")
                    if attempt < retry - 1:
                        import time
                        time.sleep(2)
                        continue
            
            return self._default_goemotions_response()
            
        except Exception as e:
            print(f"[GoEmotions] Error inesperado: {str(e)}")
            return self._default_goemotions_response()
    
    def analyze_emotion(self, text: str) -> Dict:
        """
        Analiza las emociones en el texto con pysentimiento
        Retorna: {
            'dominant_emotion': str,
            'emotions': dict con scores de cada emoción,
            'confidence': float
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
                
                if isinstance(results, list) and len(results) > 0:
                    emotions = results[0]
                    sorted_emotions = sorted(emotions, key=lambda x: x['score'], reverse=True)
                    dominant_emotion = sorted_emotions[0]['label']
                    
                    emotion_scores = {
                        emotion['label']: round(emotion['score'], 4) 
                        for emotion in emotions
                    }
                    
                    return {
                        'dominant_emotion': dominant_emotion,
                        'emotions': emotion_scores,
                        'confidence': round(sorted_emotions[0]['score'], 4)
                    }
            
            return self._default_emotion_response()
            
        except Exception as e:
            print(f"[Pysentimiento Emotion] Error: {str(e)}")
            return self._default_emotion_response()
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analiza el sentimiento en el texto con pysentimiento
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
            print(f"[Pysentimiento Sentiment] Error: {str(e)}")
            return self._default_sentiment_response()
    
    def analyze_complete_hybrid(self, text: str) -> Dict:
        """
        ANÁLISIS HÍBRIDO COMPLETO:
        1. Pysentimiento (7 emociones + sentimiento)
        2. GoEmotions (2 primarias + ~18 secundarias)
        3. Determina emoción primaria global
        """
        print(f"\n[HYBRID ANALYSIS] Iniciando análisis para: '{text[:50]}...'")
        
        # 1. Análisis pysentimiento (existente)
        print("[1/3] Analizando con Pysentimiento...")
        pysentimiento_emotion = self.analyze_emotion(text)
        pysentimiento_sentiment = self.analyze_sentiment(text)
        
        # 2. Análisis GoEmotions (nuevo)
        print("[2/3] Analizando con GoEmotions...")
        goemotions_result = self.analyze_goemotions(text)
        
        # 3. Determinar emoción primaria global
        print("[3/3] Determinando emoción primaria global...")
        primary_emotion, primary_source = self._determine_primary_emotion(
            pysentimiento_emotion,
            goemotions_result
        )
        
        # 4. Calcular intensidad emocional
        intensity = self._calculate_hybrid_intensity(
            pysentimiento_emotion.get('confidence', 0),
            pysentimiento_sentiment.get('confidence', 0),
            goemotions_result.get('dominant_primary', (None, 0))[1] if goemotions_result.get('dominant_primary') else 0
        )
        
        print(f"[RESULTADO] Primaria: {primary_emotion} ({primary_source}), Intensidad: {intensity}")
        
        return {
            'text': text,
            
            # Análisis pysentimiento (principal)
            'pysentimiento_emotion': pysentimiento_emotion,
            'pysentimiento_sentiment': pysentimiento_sentiment,
            
            # Análisis GoEmotions (complementario)
            'goemotions_primary': goemotions_result.get('primary_emotions', {}),
            'goemotions_secondary': goemotions_result.get('secondary_emotions', {}),
            
            # Emoción primaria global
            'primary_emotion': primary_emotion,
            'primary_emotion_source': primary_source,
            
            # Intensidad
            'intensity': intensity
        }
    
    def _determine_primary_emotion(self, pysentimiento_result, goemotions_result):
        """
        Determina cuál es la emoción primaria global
        Regla: Si GoEmotions detecta gratitude o pride con >70%, usarla
        Caso contrario: usar pysentimiento
        """
        pysentimiento_emotion = pysentimiento_result.get('dominant_emotion')
        goemotions_primary = goemotions_result.get('dominant_primary')
        
        # Si GoEmotions detectó gratitude o pride con alta confianza
        if goemotions_primary and goemotions_primary[1] > 0.70:
            print(f"[PRIMARY] GoEmotions ganó: {goemotions_primary[0]} ({goemotions_primary[1]*100:.1f}%)")
            return goemotions_primary[0], 'goemotions'
        
        # Caso contrario, usar pysentimiento
        print(f"[PRIMARY] Pysentimiento ganó: {pysentimiento_emotion}")
        return pysentimiento_emotion, 'pysentimiento'
    
    def _calculate_hybrid_intensity(self, pys_conf, sent_conf, go_conf):
        """Calcula intensidad considerando ambos análisis"""
        avg_confidence = (pys_conf + sent_conf + go_conf) / 3
        
        if avg_confidence >= 0.7:
            return "alta"
        elif avg_confidence >= 0.4:
            return "media"
        else:
            return "baja"
    
    def _default_goemotions_response(self):
        """Respuesta por defecto cuando GoEmotions falla"""
        return {
            'primary_emotions': {},
            'secondary_emotions': {},
            'dominant_primary': None,
            'all_emotions': {}
        }
    
    def _default_emotion_response(self) -> Dict:
        """Respuesta por defecto cuando el análisis falla"""
        return {
            'dominant_emotion': 'others',
            'emotions': {
                'joy': 0.0,
                'sadness': 0.0,
                'anger': 0.0,
                'fear': 0.0,
                'surprise': 0.0,
                'disgust': 0.0,
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


# ========== MAPEO EXTENDIDO DE EMOCIONES ==========

EMOTION_MAPPING = {
    # Pysentimiento (7)
    'joy': 'alegría',
    'sadness': 'tristeza',
    'anger': 'enojo',
    'fear': 'miedo',
    'disgust': 'disgusto',
    'surprise': 'sorpresa',
    'others': 'neutral',
    
    # GoEmotions Primarias (2)
    'gratitude': 'gratitud',
    'pride': 'orgullo',
    
    # GoEmotions Secundarias (~18)
    'admiration': 'admiración',
    'amusement': 'diversión',
    'approval': 'aprobación',
    'caring': 'cariño',
    'confusion': 'confusión',
    'curiosity': 'curiosidad',
    'desire': 'deseo',
    'disappointment': 'decepción',
    'disapproval': 'desaprobación',
    'embarrassment': 'vergüenza',
    'excitement': 'emoción',
    'grief': 'dolor',
    'love': 'amor',
    'nervousness': 'nerviosismo',
    'optimism': 'optimismo',
    'relief': 'alivio',
    'remorse': 'arrepentimiento',
    'neutral': 'neutral',
    'realization': 'comprensión'
}

SENTIMENT_MAPPING = {
    'POS': 'positivo',
    'NEG': 'negativo',
    'NEU': 'neutral'
}

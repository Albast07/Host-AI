# backend/chat/models.py

from django.conf import settings
from django.db import models

class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation with {self.user.username} on {self.start_time.strftime('%Y-%m-%d')}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    text = models.TextField()
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('bot', 'Bot')])
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Análisis de Emociones 
    dominant_emotion = models.CharField(max_length=50, blank=True, null=True)
    emotion_joy_score = models.FloatField(blank=True, null=True)
    emotion_sadness_score = models.FloatField(blank=True, null=True)
    emotion_anger_score = models.FloatField(blank=True, null=True)
    emotion_fear_score = models.FloatField(blank=True, null=True)
    emotion_disgust_score = models.FloatField(blank=True, null=True)
    emotion_surprise_score = models.FloatField(blank=True, null=True)
    emotion_others_score = models.FloatField(blank=True, null=True)

    # Análisis de Sentimiento
    sentiment = models.CharField(max_length=50, blank=True, null=True)
    sentiment_pos_score = models.FloatField(blank=True, null=True)
    sentiment_neg_score = models.FloatField(blank=True, null=True)
    sentiment_neu_score = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.sender}: {self.text[:50]}"
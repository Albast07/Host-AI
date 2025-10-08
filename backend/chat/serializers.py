# backend/chat/serializers.py
from rest_framework import serializers

class ChatResponseSerializer(serializers.Serializer):
    bot_response = serializers.CharField()
    conversation_id = serializers.IntegerField()

    class EmotionalInsightSerializer(serializers.Serializer):
        primary_emotion = serializers.CharField()
        intensity = serializers.CharField()
        educational_tip = serializers.CharField()

    emotional_insight = EmotionalInsightSerializer()

    class UserMessageAnalysisSerializer(serializers.Serializer):
        text = serializers.CharField()

        class SentimentSerializer(serializers.Serializer):
            dominant = serializers.CharField()
            Positivo = serializers.FloatField()  
            Negativo = serializers.FloatField()  
            Neutral = serializers.FloatField()   

        sentiment = SentimentSerializer()

        class EmotionSerializer(serializers.Serializer):
            dominant = serializers.CharField()
            Alegria = serializers.FloatField()   
            Tristeza = serializers.FloatField()  
            Enojo = serializers.FloatField()     
            Miedo = serializers.FloatField()     
            Disgusto = serializers.FloatField()  
            Sorpresa = serializers.FloatField()  
            Otros = serializers.FloatField()     

        emotions = EmotionSerializer()

    user_message_analysis = UserMessageAnalysisSerializer()

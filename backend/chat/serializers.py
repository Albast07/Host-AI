# backend/chat/serializers.py
from rest_framework import serializers

class ChatResponseSerializer(serializers.Serializer):
    bot_response = serializers.CharField()
    conversation_id = serializers.IntegerField()

    class EmotionalInsightSerializer(serializers.Serializer):
        primary_emotion = serializers.CharField()
        primary_emotion_source = serializers.CharField()
        intensity = serializers.CharField()
        educational_tip = serializers.CharField()
        
        class SecondaryEmotionSerializer(serializers.Serializer):
            emotion = serializers.CharField()
            score = serializers.FloatField()
        
        secondary_emotions_detected = serializers.ListField(
            child=SecondaryEmotionSerializer(),
            required=False
        )

    emotional_insight = EmotionalInsightSerializer()

    class UserMessageAnalysisSerializer(serializers.Serializer):
        text = serializers.CharField()

        class SentimentSerializer(serializers.Serializer):
            dominant = serializers.CharField()
            Positivo = serializers.FloatField()  
            Negativo = serializers.FloatField()  
            Neutral = serializers.FloatField()   

        sentiment = SentimentSerializer()

        class EmotionPrimarySerializer(serializers.Serializer):
            source = serializers.CharField()
            dominant = serializers.CharField()
            Alegria = serializers.FloatField()   
            Tristeza = serializers.FloatField()  
            Enojo = serializers.FloatField()     
            Miedo = serializers.FloatField()     
            Disgusto = serializers.FloatField()  
            Sorpresa = serializers.FloatField()  
            Otros = serializers.FloatField()     

        emotions_primary = EmotionPrimarySerializer()
        
        class GoEmotionsPrimarySerializer(serializers.Serializer):
            Gratitud = serializers.FloatField()
            Orgullo = serializers.FloatField()
        
        emotions_goemotions_primary = GoEmotionsPrimarySerializer()

    user_message_analysis = UserMessageAnalysisSerializer()

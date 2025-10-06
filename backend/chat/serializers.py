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
            Positivo = serializers.IntegerField()
            Negativo = serializers.IntegerField()
            Neutral = serializers.IntegerField()

        sentiment = SentimentSerializer()

        class EmotionSerializer(serializers.Serializer):
            dominant = serializers.CharField()
            Alegria = serializers.IntegerField()
            Tristeza = serializers.IntegerField()
            Enojo = serializers.IntegerField()
            Miedo = serializers.IntegerField()
            Disgusto = serializers.IntegerField()
            Sorpresa = serializers.IntegerField()
            Otros = serializers.IntegerField()

        emotions = EmotionSerializer()

    user_message_analysis = UserMessageAnalysisSerializer()
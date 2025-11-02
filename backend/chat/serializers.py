# backend/chat/serializers.py
from rest_framework import serializers

# Serializadores de recursos de apoyo (a nivel de módulo para evitar NameError)
class SupportTechniqueSerializer(serializers.Serializer):
    type = serializers.CharField()
    title = serializers.CharField()
    steps = serializers.ListField(child=serializers.CharField())
    duration = serializers.CharField(required=False)

class SupportResourcesSerializer(serializers.Serializer):
    available = serializers.BooleanField()
    message = serializers.CharField(allow_blank=True)
    educational_insight = serializers.CharField(allow_blank=True)
    techniques = serializers.ListField(child=SupportTechniqueSerializer())
    generated_at = serializers.CharField(required=False, allow_blank=True)
    context = serializers.DictField(child=serializers.CharField(), required=False)


class ChatResponseSerializer(serializers.Serializer):
    bot_response = serializers.CharField()
    conversation_id = serializers.IntegerField()

    class EmotionalInsightSerializer(serializers.Serializer):
        primary_emotion = serializers.CharField()
        primary_emotion_source = serializers.CharField()
        intensity = serializers.CharField()
        educational_tip = serializers.CharField(allow_blank=True)
        
        class SecondaryEmotionSerializer(serializers.Serializer):
            emotion = serializers.CharField()
            score = serializers.FloatField()
        
        secondary_emotions_detected = serializers.ListField(
            child=SecondaryEmotionSerializer(),
            required=False
        )

    emotional_insight = EmotionalInsightSerializer()

    # Recursos de apoyo opcionales (HU #7)
    support_resources = SupportResourcesSerializer(required=False, allow_null=True)

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

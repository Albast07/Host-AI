from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser

# Serializador para el modelo de usuario personalizado
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'role', 'fecha_de_nacimiento', 'date_joined']
        read_only_fields = ['id', 'date_joined']

# Serializador para el registro de usuarios
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    # Metadatos del serializador
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password', 'password_confirm', 'role', 'fecha_de_nacimiento']
    
    # Validar que las contraseñas coincidan
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Las contraseñas no coinciden")
        return attrs
    # Crear el usuario con la contraseña hasheada
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user

# Serializador para el login de usuarios
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    # Validar las credenciales del usuario
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # Si se proporcionan ambos campos, intentar autenticar
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Credenciales inválidas')
            if not user.is_active:
                raise serializers.ValidationError('Cuenta desactivada')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Debe proporcionar username y password')

# Serializador para cambiar la contraseña
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    # Validar que las nuevas contraseñas coincidan
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Las contraseñas nuevas no coinciden")
        return attrs
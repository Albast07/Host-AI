from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import CustomUser

# Serializador para el modelo de usuario personalizado
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'fecha_de_nacimiento', 'date_joined']
        read_only_fields = ['id', 'date_joined']

# Serializador para el registro de usuarios
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'username', 
            'email', 
            'password', 
            'password_confirm', 
            'first_name',      
            'last_name',       
            'role', 
            'fecha_de_nacimiento'
        ]
        extra_kwargs = {
            'first_name': {'required': True},  
            'last_name': {'required': True},   
        }
    
    def validate(self, attrs):
        # Validar que las contraseñas coincidan
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden"})
        
        # Validar que first_name y last_name no estén vacíos
        if not attrs.get('first_name', '').strip():
            raise serializers.ValidationError({"first_name": "El nombre es requerido"})
        
        if not attrs.get('last_name', '').strip():
            raise serializers.ValidationError({"last_name": "Los apellidos son requeridos"})
        
        return attrs
    
    def create(self, validated_data):
        # Remover password_confirm ya que no es parte del modelo
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        # Crear el usuario usando create_user para hashear la contraseña correctamente
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role=validated_data.get('role', 'student'),
            fecha_de_nacimiento=validated_data.get('fecha_de_nacimiento', None)
        )
        user.set_password(password)
        user.save()
        return user

# Serializador para el login de usuarios
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

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

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Las contraseñas nuevas no coinciden")
        return attrs
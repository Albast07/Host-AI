from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import login, logout
from .models import CustomUser
from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer, 
    LoginSerializer, 
    ChangePasswordSerializer
)

# ViewSet para manejar las operaciones relacionadas con usuarios
class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer

    # Permisos personalizados según la acción
    def get_permissions(self):
        if self.action in ['register', 'login']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    # Serializador personalizado según la acción
    def get_serializer_class(self):
        if self.action == 'register':
            return UserRegistrationSerializer
        elif self.action == 'login':
            return LoginSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        return UserSerializer

    # Acciones personalizadas
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)

        # Validar y guardar el nuevo usuario
        if serializer.is_valid():
            user = serializer.save()
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'Usuario registrado exitosamente'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Login de usuarios
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            login(request, user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key,
                'message': 'Login exitoso'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Cerrar sesión
    @action(detail=False, methods=['post'])
    def logout(self, request):
        try:
            request.user.auth_token.delete()
            logout(request)
            return Response({
                'message': 'Logout exitoso'
            }, status=status.HTTP_200_OK)
        except:
            return Response({
                'error': 'Error al hacer logout'
            }, status=status.HTTP_400_BAD_REQUEST)

    # Obtener y actualizar perfil del usuario
    @action(detail=False, methods=['get'])
    def profile(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Actualizar perfil del usuario
    @action(detail=False, methods=['put', 'patch'])
    def update_profile(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Cambiar contraseña
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({
                    'error': 'Contraseña actual incorrecta'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Regenerar token para forzar re-login
            Token.objects.filter(user=user).delete()
            Token.objects.create(user=user)
            
            return Response({
                'message': 'Contraseña cambiada exitosamente'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # para profesores: obtener lista de sus estudiantes
    @action(detail=False, methods=['get'])
    def my_students(self, request):
        if not request.user.is_teacher:
            return Response({
                'error': 'Solo los profesores pueden acceder a esta función'
            }, status=status.HTTP_403_FORBIDDEN)
        
        students = request.user.students.all()
        serializer = UserSerializer(students, many=True)
        return Response(serializer.data)
    
    # para profesores: asignar un estudiante
    @action(detail=False, methods=['post'])
    def assign_student(self, request):
        """Para profesores: asignar un estudiante"""
        if not request.user.is_teacher:
            return Response({
                'error': 'Solo los profesores pueden asignar estudiantes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        student_id = request.data.get('student_id')
        if not student_id:
            return Response({
                'error': 'student_id es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            student = CustomUser.objects.get(id=student_id, role='student')
            request.user.students.add(student)
            return Response({
                'message': f'Estudiante {student.username} asignado exitosamente'
            }, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Estudiante no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)

    #para profesores: ver estudiantes disponibles para asignar
    @action(detail=False, methods=['get'])
    def available_students(self, request):
        if not request.user.is_teacher:
            return Response({
                'error': 'Solo los profesores pueden ver estudiantes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Todos los estudiantes
        all_students = CustomUser.objects.filter(role='student')
        serializer = UserSerializer(all_students, many=True)
        return Response(serializer.data)
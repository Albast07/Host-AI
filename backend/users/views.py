from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import login, logout
from .models import CustomUser, Course
from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer, 
    LoginSerializer, 
    ChangePasswordSerializer,
    CourseSerializer,
    CourseListSerializer
)
from .permissions import IsAdminUser, IsAdminOrTeacher

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

    # Administrador: listar profesores
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def teachers(self, request):
        """Lista de usuarios con rol 'teacher' (solo admin)."""
        teachers = CustomUser.objects.filter(role='teacher').order_by('username')
        serializer = UserSerializer(teachers, many=True)
        return Response(serializer.data)

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


# ViewSet para manejar operaciones CRUD de Courses
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by('-start_date')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        return CourseSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # Solo admins pueden crear, editar o eliminar cursos
            permission_classes = [IsAdminUser]
        elif self.action in ['list', 'retrieve']:
            # Admins y profesores pueden ver cursos
            permission_classes = [IsAdminOrTeacher]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """Listar cursos (filtrados según el rol del usuario)"""
        user = request.user
        
        if user.is_admin:
            # Admin ve todos los cursos
            queryset = self.get_queryset()
        elif user.is_teacher:
            # Profesor solo ve sus cursos asignados
            queryset = Course.objects.filter(teacher=user).order_by('-start_date')
        else:
            return Response({
                'error': 'No tienes permisos para ver cursos'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_teacher(self, request, pk=None):
        """Asignar un profesor a un curso (solo admin)"""
        course = self.get_object()
        teacher_id = request.data.get('teacher_id')
        
        if not teacher_id:
            return Response({
                'error': 'teacher_id es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            teacher = CustomUser.objects.get(id=teacher_id, role='teacher')
            course.teacher = teacher
            course.save()
            
            serializer = CourseSerializer(course)
            return Response({
                'message': f'Profesor {teacher.username} asignado exitosamente',
                'course': serializer.data
            }, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Profesor no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def unassign_teacher(self, request, pk=None):
        """Desasignar el profesor de un curso (solo admin)."""
        course = self.get_object()
        course.teacher = None
        course.save()
        return Response({
            'message': 'Profesor desasignado exitosamente',
            'course': CourseSerializer(course).data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrTeacher])
    def add_students(self, request, pk=None):
        """Agregar estudiantes a un curso (admin o profesor del curso)"""
        course = self.get_object()
        user = request.user
        
        # Verificar que sea admin o el profesor asignado al curso
        if not user.is_admin and course.teacher != user:
            return Response({
                'error': 'Solo el admin o el profesor asignado pueden agregar estudiantes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        student_ids = request.data.get('student_ids', [])
        
        if not student_ids or not isinstance(student_ids, list):
            return Response({
                'error': 'student_ids debe ser una lista de IDs'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        added_students = []
        errors = []
        
        for student_id in student_ids:
            try:
                student = CustomUser.objects.get(id=student_id, role='student')
                course.students.add(student)
                added_students.append(student.username)
            except CustomUser.DoesNotExist:
                errors.append(f'Estudiante con ID {student_id} no encontrado')
        
        return Response({
            'message': f'{len(added_students)} estudiante(s) agregado(s) exitosamente',
            'added_students': added_students,
            'errors': errors
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrTeacher])
    def remove_student(self, request, pk=None):
        """Remover un estudiante de un curso (admin o profesor del curso)"""
        course = self.get_object()
        user = request.user
        
        # Verificar que sea admin o el profesor asignado al curso
        if not user.is_admin and course.teacher != user:
            return Response({
                'error': 'Solo el admin o el profesor asignado pueden remover estudiantes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        student_id = request.data.get('student_id')
        
        if not student_id:
            return Response({
                'error': 'student_id es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            student = CustomUser.objects.get(id=student_id, role='student')
            course.students.remove(student)
            
            return Response({
                'message': f'Estudiante {student.username} removido exitosamente'
            }, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'Estudiante no encontrado'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'], permission_classes=[IsAdminOrTeacher])
    def students_list(self, request, pk=None):
        """Ver lista de estudiantes del curso (admin o profesor del curso)"""
        course = self.get_object()
        user = request.user
        
        # Verificar que sea admin o el profesor asignado al curso
        if not user.is_admin and course.teacher != user:
            return Response({
                'error': 'Solo el admin o el profesor asignado pueden ver los estudiantes'
            }, status=status.HTTP_403_FORBIDDEN)
        
        students = course.students.all()
        serializer = UserSerializer(students, many=True)
        
        return Response({
            'course_name': course.name,
            'course_code': course.code,
            'total_students': students.count(),
            'students': serializer.data
        }, status=status.HTTP_200_OK)

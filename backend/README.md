# Backend - Sistema de Chatbot con Análisis Emocional

Backend construido con Django REST Framework que proporciona una API REST completa para gestión de usuarios, conversaciones con IA y análisis emocional en tiempo real.

# Tabla de Contenidos

- [Tecnologías](#-tecnologías)
- [Arquitectura](#-arquitectura)
- [Instalación y Configuración](#-instalación-y-configuración)
- [Endpoints de la API](#-endpoints-de-la-api)
- [Modelos de Base de Datos](#-modelos-de-base-de-datos)
- [Análisis Emocional](#-análisis-emocional)
- [Despliegue](#-despliegue)
- [Notas para Frontend](#-notas-para-frontend)

---

# Tecnologías

- **Framework**: Django 5.2.6 + Django REST Framework 3.14.0
- **Base de Datos**: PostgreSQL 15
- **Autenticación**: Token Authentication (DRF)
- **IA**: Google Gemini API
- **CORS**: django-cors-headers
- **Containerización**: Docker + Docker Compose
- **Servidor**: Gunicorn + Whitenoise (producción)

---

# Arquitectura

```
backend/
├── config/                 # Configuración principal de Django
│   ├── settings.py        # Configuración del proyecto
│   ├── urls.py            # Rutas principales
│   └── wsgi.py            # Entrada WSGI
├── users/                 # App de gestión de usuarios
│   ├── models.py          # Modelo CustomUser
│   ├── serializers.py     # Serializers para API
│   ├── views.py           # ViewSets de usuarios
│   └── urls.py            # Rutas de usuarios
├── chat/                  # App de chat e IA
│   ├── models.py          # Conversation, Message
│   ├── views.py           # Lógica de chat y dashboard
│   ├── emotion_analyzer.py # Análisis emocional
│   └── urls.py            # Rutas de chat
├── manage.py              # CLI de Django
├── requirements.txt       # Dependencias Python
└── dockerfile             # Imagen Docker
```

# Apps del Proyecto

1. **users**: Gestión de usuarios, autenticación y roles (estudiante/profesor)
2. **chat**: Conversaciones con IA, análisis emocional y estadísticas

---

# Instalación y Configuración

# Opción 1: Con Docker (Recomendado)

```bash
# 1. Clonar el proyecto y navegar a la raíz
cd D:\Projects\Host

# 2. Crear archivo .env desde el template
cp .env.example .env

# 3. Editar .env con tus credenciales (ver sección Variables de Entorno)

# 4. Levantar los servicios
docker-compose up -d

# 5. Aplicar migraciones
docker-compose exec backend python manage.py migrate

# 6. Crear superusuario
docker-compose exec backend python manage.py createsuperuser
```

# Opción 2: Local (Desarrollo)

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 4. Aplicar migraciones
python manage.py migrate

# 5. Crear superusuario
python manage.py createsuperuser

# 6. Ejecutar servidor
python manage.py runserver
```

# Variables de Entorno (.env)

env
# PostgreSQL (Docker)
POSTGRES_DB=chatbot_db
POSTGRES_USER=tu_usuario
POSTGRES_PASSWORD=password

# Django Database
DB_NAME=chatbot_db
DB_USER=usuario
DB_PASSWORD=password_seguro
DB_HOST=db                    # "localhost" si corres local
DB_PORT=5432

# Django Core
SECRET_KEY=genera-un-secret-key-seguro
DEBUG=True                    # False en producción
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Google Gemini API
GEMINI_API_KEY=clave_api_gemini

# CORS (Frontend URLs)
CORS_ALLOWED_ORIGINS=http://localhost:4200,https://tu-app.vercel.app


- Obtén GEMINI_API_KEY en: https://makersuite.google.com/app/apikey


# Endpoints de la API

**Base URL**: `http://localhost:8000/api/v1`

# Autenticación

Todos los endpoints (excepto registro y login) requieren el header:
```
Authorization: Token <token_aqui>
```

### Users Endpoints

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/users/register/` | Registrar nuevo usuario | No |
| POST | `/users/login/` | Iniciar sesión | No |
| POST | `/users/logout/` | Cerrar sesión | Sí |
| GET | `/users/profile/` | Obtener perfil del usuario actual | Sí |
| PUT/PATCH | `/users/profile/` | Actualizar perfil | Sí |
| GET | `/users/my-students/` | Listar estudiantes (solo profesores) | Sí |
| POST | `/users/add-student/` | Agregar estudiante (solo profesores) | Sí |
| DELETE | `/users/remove-student/{user_id}/` | Remover estudiante | Sí |

# Ejemplos de Requests

**Registro**
```json
POST /api/v1/users/register/
Content-Type: application/json

{
  "username": "juan_perez",
  "email": "juan@example.com",
  "password": "Password123!",
  "fecha_de_nacimiento": "2000-05-15",
  "role": "student"  // "student" o "teacher"
}

// Response 201 Created
{
  "id": 1,
  "username": "juan_perez",
  "email": "juan@example.com",
  "role": "student",
  "fecha_de_nacimiento": "2000-05-15",
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

**Login**
```json
POST /api/v1/users/login/
Content-Type: application/json

{
  "username": "juan_perez",
  "password": "Password123!"
}

// Response 200 OK
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": {
    "id": 1,
    "username": "juan_perez",
    "email": "juan@example.com",
    "role": "student"
  }
}
```

**Obtener Perfil**
```json
GET /api/v1/users/profile/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

// Response 200 OK
{
  "id": 1,
  "username": "juan_perez",
  "email": "juan@example.com",
  "fecha_de_nacimiento": "2000-05-15",
  "role": "student",
  "is_student": true,
  "is_teacher": false
}
```

# Chat Endpoints

| Método | Endpoint | Descripción | Auth |
|--------|----------|-------------|------|
| POST | `/chat/` | Enviar mensaje y recibir respuesta de IA | Sí |
| GET | `/chat/dashboard/` | Obtener estadísticas emocionales | Sí |
| GET | `/chat/dashboard/export-pdf/` | Descargar reporte PDF (profesor) | Sí |

# Ejemplos de Requests

**Enviar Mensaje al Chatbot**
```json
POST /api/v1/chat/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b
Content-Type: application/json

{
  "text": "Me siento muy feliz hoy porque aprobé mi examen"
}

// Response 200 OK
{
  "user_message": {
    "id": 42,
    "text": "Me siento muy feliz hoy porque aprobé mi examen",
    "sender": "user",
    "timestamp": "2025-10-19T14:30:00Z",
    
    // Análisis emocional del mensaje del usuario
    "dominant_emotion": "joy",
    "primary_emotion": "joy",
    "sentiment": "positive",
    
    "emotion_scores": {
      "joy": 0.85,
      "sadness": 0.02,
      "anger": 0.01,
      "fear": 0.01,
      "disgust": 0.01,
      "surprise": 0.08,
      "others": 0.02
    },
    
    "sentiment_scores": {
      "pos": 0.92,
      "neg": 0.02,
      "neu": 0.06
    },
    
    "secondary_emotions": {
      "gratitude": 0.25,
      "pride": 0.45,
      "admiration": 0.15
    }
  },
  
  "bot_response": {
    "id": 43,
    "text": "¡Felicitaciones por aprobar tu examen! Es normal sentirse feliz...",
    "sender": "bot",
    "timestamp": "2025-10-19T14:30:02Z"
  },
  
  "conversation_id": 7
}
```

**Obtener Dashboard de Emociones**
```json
GET /api/v1/chat/dashboard/
Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b

// Response 200 OK
{
  "total_messages": 156,
  "total_conversations": 12,
  "emotion_distribution": {
    "joy": 42,
    "sadness": 28,
    "anger": 15,
    "fear": 18,
    "surprise": 32,
    "disgust": 8,
    "others": 13
  },
  "sentiment_distribution": {
    "positive": 89,
    "negative": 45,
    "neutral": 22
  },
  "average_emotion_scores": {
    "joy": 0.35,
    "sadness": 0.18,
    "anger": 0.12,
    "fear": 0.15,
    "surprise": 0.10,
    "disgust": 0.05,
    "others": 0.05
  },
  "top_secondary_emotions": {
    "gratitude": 35,
    "curiosity": 28,
    "nervousness": 22
  },
  "recent_conversations": [
    {
      "id": 12,
      "start_time": "2025-10-19T10:00:00Z",
      "message_count": 8,
      "dominant_emotion": "joy"
    }
  ]
}
```

---

# Endpoints Admin (Cursos y Profesores)

- `GET /api/v1/users/teachers/` (solo admin): Lista de profesores.
- `GET /api/v1/courses/` (admin: todos; profesor: solo propios)
- `POST /api/v1/courses/{id}/assign_teacher/` (solo admin): Body `{ "teacher_id": <int> }`.
- `POST /api/v1/courses/{id}/unassign_teacher/` (solo admin): Desasigna al profesor.

# Modelos de Base de Datos

# CustomUser (users/models.py)

Modelo extendido de usuario con roles.

```python
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    fecha_de_nacimiento = models.DateField(null=True, blank=True)
    role = models.CharField(
        max_length=10, 
        choices=[('student', 'Estudiante'), ('teacher', 'Profesor')],
        default='student'
    )
    students = models.ManyToManyField('self', ...)  # Solo para profesores
```

**Propiedades útiles**:
- `is_student`: Boolean
- `is_teacher`: Boolean

# Conversation (chat/models.py)

Agrupa mensajes de una sesión de chat.

```python
class Conversation(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
```

# Message (chat/models.py)

Almacena cada mensaje con su análisis emocional completo.

```python
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', ...)
    text = models.TextField()
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('bot', 'Bot')])
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Emociones primarias (PysentImiento - 7 emociones)
    dominant_emotion = models.CharField(max_length=50, blank=True, null=True)
    emotion_joy_score = models.FloatField(blank=True, null=True)
    emotion_sadness_score = models.FloatField(blank=True, null=True)
    emotion_anger_score = models.FloatField(blank=True, null=True)
    emotion_fear_score = models.FloatField(blank=True, null=True)
    emotion_disgust_score = models.FloatField(blank=True, null=True)
    emotion_surprise_score = models.FloatField(blank=True, null=True)
    emotion_others_score = models.FloatField(blank=True, null=True)
    
    # Emociones adicionales (GoEmotions)
    emotion_gratitude_score = models.FloatField(blank=True, null=True)
    emotion_pride_score = models.FloatField(blank=True, null=True)
    
    # Emociones secundarias (JSON)
    secondary_emotions = models.JSONField(blank=True, null=True)
    # Ejemplo: {"admiration": 0.15, "curiosity": 0.23, "nervousness": 0.45}
    
    # Emoción global
    primary_emotion = models.CharField(max_length=50, blank=True, null=True)
    primary_emotion_source = models.CharField(
        max_length=20,
        choices=[('pysentimiento', 'Pysentimiento'), ('goemotions', 'GoEmotions')],
        blank=True, null=True
    )
    
    # Sentimiento
    sentiment = models.CharField(max_length=50, blank=True, null=True)
    sentiment_pos_score = models.FloatField(blank=True, null=True)
    sentiment_neg_score = models.FloatField(blank=True, null=True)
    sentiment_neu_score = models.FloatField(blank=True, null=True)
```

---

# Análisis Emocional

El sistema utiliza modelos de NLP especializados para analizar emociones:

# Emociones Primarias (PysentImiento)
- **joy** (alegría)
- **sadness** (tristeza)
- **anger** (enojo)
- **fear** (miedo)
- **disgust** (asco)
- **surprise** (sorpresa)
- **others** (otras)

# Emociones Adicionales (GoEmotions)
- **gratitude** (gratitud)
- **pride** (orgullo)
- **admiration** (admiración)
- **curiosity** (curiosidad)
- **nervousness** (nerviosismo)

# Análisis de Sentimiento
- **positive** (positivo)
- **negative** (negativo)
- **neutral** (neutral)

# Flujo del Análisis

```
Usuario envía mensaje
        ↓
Análisis emocional en backend (emotion_analyzer.py)
        ↓
Guardado en BD con scores
        ↓
Mensaje enviado a Gemini API
        ↓
Respuesta del bot guardada
        ↓
Retorno al frontend con análisis completo
```

---

# Despliegue

# Producción en Render

1. **Crear Base de Datos PostgreSQL en Render**
   - Dashboard → New → PostgreSQL
   - Copiar `Internal Database URL`

2. **Configurar Variables de Entorno en Render**
   ```
   DATABASE_URL=postgresql://user:pass@host:port/db
   SECRET_KEY=<generar-nuevo>
   DEBUG=False
   ALLOWED_HOSTS=app.onrender.com
   GEMINI_API_KEY=<api-key>
   CORS_ALLOWED_ORIGINS=https://frontend.vercel.app
   ```

3. **Configurar Build & Deploy**
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - Start Command: `gunicorn config.wsgi:application`

# Comandos Útiles

```bash
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Recolectar archivos estáticos
python manage.py collectstatic

# Ejecutar tests
python manage.py test

# Shell de Django
python manage.py shell
```

---

# Notas para Frontend

# Headers Requeridos

Todas las peticiones autenticadas deben incluir:

```javascript
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Token ${userToken}`
};
```

# Manejo de Errores

La API retorna errores en formato JSON:

```json
// Error 400 - Bad Request
{
  "field_name": ["Error message"]
}

// Error 401 - Unauthorized
{
  "detail": "Invalid token."
}

// Error 404 - Not Found
{
  "detail": "Not found."
}

// Error 500 - Server Error
{
  "error": "Internal server error"
}
```

# CORS

El backend ya está configurado para aceptar requests desde:
- `http://localhost:4200` (desarrollo)
- `https://*.vercel.app` (producción)

Si necesitas agregar más orígenes, edita `CORS_ALLOWED_ORIGINS` en `.env`.

# Paginación

Los endpoints que retornan listas usan paginación:

```json
GET /api/v1/users/my-students/?page=2

{
  "count": 45,
  "next": "http://api.example.com/api/v1/users/my-students/?page=3",
  "previous": "http://api.example.com/api/v1/users/my-students/?page=1",
  "results": [...]
}
```
# Soporte

Para problemas o consultas sobre el backend:

1. Revisa los logs: `docker-compose logs backend`
2. Verifica las variables de entorno en `.env`
3. Asegúrate de que PostgreSQL esté corriendo
4. Revisa que GEMINI_API_KEY sea válida

---

**Última actualización**: Octubre 2025  
**Versión**: 1.0.0

# backend/chat/admin.py
from django.contrib import admin
from .models import Conversation, Message

# Los modelos de Conversation y Message NO se registran en el admin
# para proteger la privacidad de los estudiantes.
# Solo el equipo técnico con acceso directo a la base de datos puede ver estos datos.

# Si en el futuro se necesita acceso, descomentar las siguientes líneas:
# admin.site.register(Conversation)
# admin.site.register(Message)

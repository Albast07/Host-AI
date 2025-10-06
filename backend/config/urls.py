from django.contrib import admin
from django.urls import path, include # Asegúrate de que 'include' esté aquí

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('users.urls')), 
    path('api/v1/chat/', include('chat.urls')), 
]
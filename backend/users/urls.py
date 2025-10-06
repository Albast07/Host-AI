from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet

# Router automático - Los endpoints se generan automáticamente desde UserViewSet
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]

# Los endpoints no se definen aquí porque se crean automáticamente 
# a partir de los métodos @action() en UserViewSet
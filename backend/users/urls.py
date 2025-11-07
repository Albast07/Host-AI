from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, CourseViewSet

# Router automático - Los endpoints se generan automáticamente desde UserViewSet y CourseViewSet
router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'courses', CourseViewSet, basename='course')

urlpatterns = [
    path('', include(router.urls)),
]

# Los endpoints no se definen aquí porque se crean automáticamente 
# a partir de los métodos @action() en UserViewSet
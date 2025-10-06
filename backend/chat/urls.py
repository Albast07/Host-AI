from django.urls import path
from .views import ChatAPIView, DashboardStatsView

urlpatterns = [
    path('', ChatAPIView.as_view(), name='chat-api'),
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
]
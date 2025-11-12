from django.urls import path
from .views import (
    ChatAPIView,
    DashboardStatsView,
    ExportDashboardPDFView,
    CourseEmotionRecommendationView,
)

urlpatterns = [
    path('', ChatAPIView.as_view(), name='chat-api'),
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/export-pdf/', ExportDashboardPDFView.as_view(), name='export-dashboard-pdf'),
    path('courses/<int:course_id>/recommendations/', CourseEmotionRecommendationView.as_view(), name='course-emotion-recommendations'),
]

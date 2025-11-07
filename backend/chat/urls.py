from django.urls import path
from .views import ChatAPIView, DashboardStatsView, ExportDashboardPDFView

urlpatterns = [
    path('', ChatAPIView.as_view(), name='chat-api'),
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/export-pdf/', ExportDashboardPDFView.as_view(), name='export-dashboard-pdf'),
]
from django.urls import path
from apps.monitoring.views import MetricsDashboardView, ReconciliationReportView

urlpatterns = [
    path('', MetricsDashboardView.as_view(), name='metrics-dashboard'),
    path('reconciliation/', ReconciliationReportView.as_view(), name='metrics-reconciliation'),
]

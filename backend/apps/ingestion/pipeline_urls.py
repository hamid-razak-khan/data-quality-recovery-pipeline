from django.urls import path
from apps.ingestion.views import PipelineRunTriggerView, PipelineRunListView, PipelineRunDetailView

urlpatterns = [
    path('run/', PipelineRunTriggerView.as_view(), name='pipeline-run'),
    path('runs/', PipelineRunListView.as_view(), name='pipeline-runs-list'),
    path('runs/<uuid:run_id>/', PipelineRunDetailView.as_view(), name='pipeline-run-detail'),
]

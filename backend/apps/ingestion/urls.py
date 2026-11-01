from django.urls import path
from apps.ingestion.views import FileUploadView

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='ingestion-upload'),
]

from django.urls import path
from apps.processing.views import DataGenerateView

urlpatterns = [
    path('generate/', DataGenerateView.as_view(), name='data-generate'),
]

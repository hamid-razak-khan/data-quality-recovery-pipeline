from django.urls import path
from apps.quarantine.views import (
    QuarantineRecordListView,
    QuarantineRecordDetailView,
    QuarantineCorrectionView,
    QuarantineSummaryView,
)

urlpatterns = [
    path('', QuarantineRecordListView.as_view(), name='quarantine-list'),
    path('summary/', QuarantineSummaryView.as_view(), name='quarantine-summary'),
    path('<uuid:quarantine_id>/', QuarantineRecordDetailView.as_view(), name='quarantine-detail'),
    path('<uuid:quarantine_id>/correct/', QuarantineCorrectionView.as_view(), name='quarantine-correct'),
]

from django.urls import path
from apps.replay.views import (
    ReplayTriggerView,
    ReplayHistoryListView,
    ReplayDetailView,
)

urlpatterns = [
    path('', ReplayTriggerView.as_view(), name='replay-trigger'),
    path('history/', ReplayHistoryListView.as_view(), name='replay-history-list'),
    path('<uuid:replay_id>/', ReplayDetailView.as_view(), name='replay-detail'),
]

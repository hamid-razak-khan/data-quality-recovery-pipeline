from rest_framework import serializers
from apps.replay.models import ReplayHistory


class ReplayHistorySerializer(serializers.ModelSerializer):
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = ReplayHistory
        fields = [
            'replay_id',
            'run_id',
            'total_submitted',
            'successful_count',
            'failed_count',
            'replayed_record_ids',
            'status',
            'error_summary',
            'success_rate',
            'started_at',
            'completed_at',
        ]

    def get_success_rate(self, obj):
        if obj.total_submitted > 0:
            return round((obj.successful_count / obj.total_submitted) * 100, 2)
        return 0.0

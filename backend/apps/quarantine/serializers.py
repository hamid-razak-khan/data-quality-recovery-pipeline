from rest_framework import serializers
from apps.quarantine.models import QuarantineRecord, CorrectionHistory


class CorrectionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectionHistory
        fields = [
            'correction_id',
            'previous_payload',
            'corrected_payload',
            'changed_fields',
            'corrected_by',
            'correction_notes',
            'created_at',
        ]


class QuarantineRecordListSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuarantineRecord
        fields = [
            'quarantine_id',
            'record_id',
            'source_file',
            'source_row_number',
            'run_id',
            'error_code',
            'error_reason',
            'validation_stage',
            'status',
            'attempt_count',
            'created_at',
            'updated_at',
            'replayed_at',
        ]


class QuarantineRecordDetailSerializer(serializers.ModelSerializer):
    corrections = CorrectionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = QuarantineRecord
        fields = [
            'quarantine_id',
            'record_id',
            'source_file',
            'source_row_number',
            'run_id',
            'raw_record',
            'corrected_record',
            'error_code',
            'error_reason',
            'validation_stage',
            'validation_errors',
            'status',
            'attempt_count',
            'corrections',
            'created_at',
            'updated_at',
            'replayed_at',
        ]

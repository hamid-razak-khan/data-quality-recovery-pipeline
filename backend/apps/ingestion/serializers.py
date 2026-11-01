from rest_framework import serializers
from apps.ingestion.models import SourceFile, PipelineRun, SourceRecord


class SourceFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceFile
        fields = [
            'file_id',
            'filename',
            'file_path',
            'file_format',
            'file_size_bytes',
            'file_hash',
            'status',
            'uploaded_at',
        ]


class PipelineRunSerializer(serializers.ModelSerializer):
    success_rate = serializers.SerializerMethodField()
    detected_schema = serializers.SerializerMethodField()
    throughput_rps = serializers.SerializerMethodField()

    class Meta:
        model = PipelineRun
        fields = [
            'run_id',
            'filename',
            'start_time',
            'end_time',
            'total_records',
            'valid_records',
            'rejected_records',
            'processed_records',
            'replayed_records',
            'failed_records',
            'execution_duration',
            'run_status',
            'failure_reason',
            'metadata',
            'detected_schema',
            'throughput_rps',
            'success_rate',
            'created_at',
        ]

    def get_success_rate(self, obj):
        if obj.total_records > 0:
            return round((obj.valid_records / obj.total_records) * 100, 2)
        return 0.0

    def get_detected_schema(self, obj):
        if obj.metadata and isinstance(obj.metadata, dict):
            val = obj.metadata.get('schema_detected')
            if val:
                return val
        fn = (obj.filename or '').lower()
        if 'telemetry' in fn:
            return 'telemetry'
        if 'generic' in fn:
            return 'generic'
        if 'order' in fn:
            return 'ecommerce'
        return 'generic'

    def get_throughput_rps(self, obj):
        if obj.execution_duration and float(obj.execution_duration) > 0 and obj.total_records:
            return round(obj.total_records / float(obj.execution_duration), 1)
        return 0.0


class SourceRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceRecord
        fields = [
            'record_id',
            'source_file',
            'source_row_number',
            'raw_data',
            'is_valid',
            'created_at',
        ]

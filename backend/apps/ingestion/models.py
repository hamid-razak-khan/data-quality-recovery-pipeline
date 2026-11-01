import uuid
from django.db import models


class SourceFile(models.Model):
    file_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255, db_index=True)
    file_path = models.CharField(max_length=512)
    file_format = models.CharField(max_length=16)  # CSV, JSON
    file_size_bytes = models.BigIntegerField()
    file_hash = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=32, default='UPLOADED')  # UPLOADED, PROCESSED, FAILED
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'source_files'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} ({self.file_format})"


class PipelineRun(models.Model):
    STATUS_CHOICES = [
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('COMPLETED_WITH_ERRORS', 'Completed With Errors'),
        ('FAILED', 'Failed'),
    ]

    run_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_file = models.ForeignKey(SourceFile, on_delete=models.SET_NULL, null=True, blank=True, related_name='runs')
    filename = models.CharField(max_length=255)
    start_time = models.DateTimeField(auto_now_add=True, db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_records = models.IntegerField(default=0)
    valid_records = models.IntegerField(default=0)
    rejected_records = models.IntegerField(default=0)
    processed_records = models.IntegerField(default=0)
    replayed_records = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)
    execution_duration = models.FloatField(default=0.0)
    run_status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='RUNNING', db_index=True)
    failure_reason = models.TextField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pipeline_runs'
        ordering = ['-start_time']

    def __str__(self):
        return f"Run {self.run_id} - {self.run_status}"


class SourceRecord(models.Model):
    record_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey(PipelineRun, on_delete=models.CASCADE, related_name='source_records')
    source_file = models.CharField(max_length=255)
    source_row_number = models.IntegerField()
    raw_data = models.JSONField()
    is_valid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'source_records'
        indexes = [
            models.Index(fields=['run', 'source_row_number']),
        ]

    def __str__(self):
        return f"Record {self.record_id} row {self.source_row_number}"

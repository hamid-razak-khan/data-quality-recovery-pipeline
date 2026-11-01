import uuid
from django.db import models


class QuarantineRecord(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Correction'),
        ('CORRECTED', 'Corrected - Ready for Replay'),
        ('REPLAYED', 'Successfully Replayed'),
        ('FAILED', 'Replay Failed'),
    ]

    VALIDATION_STAGES = [
        ('SCHEMA', 'Schema Validation'),
        ('BUSINESS', 'Business Validation'),
        ('SYSTEM', 'System Error'),
    ]

    quarantine_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    record_id = models.CharField(max_length=128, db_index=True)
    source_file = models.CharField(max_length=255)
    source_row_number = models.IntegerField()
    run_id = models.UUIDField(db_index=True)
    raw_record = models.JSONField(help_text="Original raw source payload as received")
    corrected_record = models.JSONField(null=True, blank=True, help_text="Operator-corrected payload")
    error_code = models.CharField(max_length=64, db_index=True)
    error_reason = models.TextField()
    validation_stage = models.CharField(max_length=32, choices=VALIDATION_STAGES, default='SCHEMA')
    validation_errors = models.JSONField(default=list, help_text="Detailed array of all validation errors")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    attempt_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    replayed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'quarantine_records'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'error_code']),
            models.Index(fields=['run_id', 'status']),
            models.Index(fields=['source_file', 'source_row_number']),
        ]

    def __str__(self):
        return f"Quarantine {self.record_id} [{self.status}] - {self.error_code}"


class CorrectionHistory(models.Model):
    correction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quarantine_record = models.ForeignKey(
        QuarantineRecord,
        on_delete=models.CASCADE,
        related_name='corrections'
    )
    previous_payload = models.JSONField()
    corrected_payload = models.JSONField()
    changed_fields = models.JSONField(default=dict)
    corrected_by = models.CharField(max_length=128, default='operator')
    correction_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'correction_history'
        ordering = ['-created_at']

    def __str__(self):
        return f"Correction for {self.quarantine_record.record_id} at {self.created_at}"

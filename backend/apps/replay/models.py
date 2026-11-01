import uuid
from django.db import models


class ReplayHistory(models.Model):
    STATUS_CHOICES = [
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    replay_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run_id = models.UUIDField(null=True, blank=True, db_index=True)
    total_submitted = models.IntegerField(default=0)
    successful_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    replayed_record_ids = models.JSONField(default=list)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='COMPLETED')
    error_summary = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'replay_history'
        ordering = ['-started_at']

    def __str__(self):
        return f"Replay {self.replay_id} [{self.status}] ({self.successful_count}/{self.total_submitted} successful)"

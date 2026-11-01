"""
Controlled Replay Engine.
Core business requirement:
Replays ONLY eligible corrected records without re-processing previously successful records.
Guarantees idempotency, atomic claiming, re-validation against active schema, and execution history.
"""
import uuid
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.utils import timezone
from apps.quarantine.models import QuarantineRecord
from apps.replay.models import ReplayHistory
from apps.processing.models import Customer
from data_pipeline.engine.schema_registry import SchemaRegistry
from data_pipeline.engine.schema_validator import SchemaValidator
from data_pipeline.engine.business_validator import BusinessValidator
from data_pipeline.engine.transformer import Transformer
from data_pipeline.engine.publisher import Publisher


class ReplayEngine:
    @classmethod
    def execute_replay(
        cls,
        quarantine_ids: Optional[List[str]] = None,
        replay_all_eligible: bool = False,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes controlled replay on eligible corrected records.
        Records MUST have status == 'CORRECTED'.
        Never reprocesses previously successful ('REPLAYED') records.
        """
        replay_history = ReplayHistory.objects.create(
            replay_id=uuid.uuid4(),
            run_id=run_id,
            status='RUNNING',
            started_at=timezone.now(),
        )

        with transaction.atomic():
            qs = QuarantineRecord.objects.select_for_update(skip_locked=True).filter(
                status='CORRECTED'
            )

            if quarantine_ids:
                qs = qs.filter(quarantine_id__in=quarantine_ids)
            elif not replay_all_eligible:
                replay_history.status = 'COMPLETED'
                replay_history.completed_at = timezone.now()
                replay_history.save()
                return {
                    'replay_id': str(replay_history.replay_id),
                    'total_submitted': 0,
                    'successful_count': 0,
                    'failed_count': 0,
                    'status': 'COMPLETED',
                    'message': 'No records selected for replay.',
                }

            eligible_records = list(qs)

        total_submitted = len(eligible_records)
        successful_ids = []
        failed_records_info = []

        if total_submitted == 0:
            replay_history.total_submitted = 0
            replay_history.successful_count = 0
            replay_history.failed_count = 0
            replay_history.status = 'COMPLETED'
            replay_history.completed_at = timezone.now()
            replay_history.save()
            return {
                'replay_id': str(replay_history.replay_id),
                'total_submitted': 0,
                'successful_count': 0,
                'failed_count': 0,
                'status': 'COMPLETED',
                'message': 'No eligible corrected records found to replay.',
            }

        valid_customer_ids = set(Customer.objects.values_list('customer_id', flat=True))

        transformed_to_publish = []
        records_to_mark_replayed = []
        records_to_mark_failed = []

        for q_rec in eligible_records:
            q_rec.attempt_count += 1
            payload = q_rec.corrected_record or q_rec.raw_record
            schema = SchemaRegistry.detect_schema(payload)

            # Step 1: Re-validate Schema
            is_schema_valid, schema_errors = SchemaValidator.validate_record(
                payload,
                schema=schema,
                source_file=q_rec.source_file,
                source_row_number=q_rec.source_row_number
            )

            if not is_schema_valid:
                q_rec.status = 'FAILED'
                q_rec.validation_stage = 'SCHEMA'
                q_rec.error_code = schema_errors[0]['error_code']
                q_rec.error_reason = "; ".join([e['error_reason'] for e in schema_errors])
                q_rec.validation_errors = schema_errors
                records_to_mark_failed.append(q_rec)
                failed_records_info.append({
                    'quarantine_id': str(q_rec.quarantine_id),
                    'record_id': q_rec.record_id,
                    'errors': schema_errors
                })
                continue

            # Step 2: Re-validate Business Rules
            is_biz_valid, biz_errors = BusinessValidator.validate_record(
                payload,
                schema=schema,
                valid_customer_ids=valid_customer_ids,
                source_file=q_rec.source_file,
                source_row_number=q_rec.source_row_number
            )

            if not is_biz_valid:
                q_rec.status = 'FAILED'
                q_rec.validation_stage = 'BUSINESS'
                q_rec.error_code = biz_errors[0]['error_code']
                q_rec.error_reason = "; ".join([e['error_reason'] for e in biz_errors])
                q_rec.validation_errors = biz_errors
                records_to_mark_failed.append(q_rec)
                failed_records_info.append({
                    'quarantine_id': str(q_rec.quarantine_id),
                    'record_id': q_rec.record_id,
                    'errors': biz_errors
                })
                continue

            # Validation passed! Transform for target publishing
            transformed = Transformer.transform_record(
                payload,
                schema=schema,
                run_id=str(q_rec.run_id),
                source_file=q_rec.source_file,
                source_row_number=q_rec.source_row_number
            )
            transformed_to_publish.append(transformed)

            q_rec.status = 'REPLAYED'
            q_rec.replayed_at = timezone.now()
            records_to_mark_replayed.append(q_rec)
            successful_ids.append(str(q_rec.quarantine_id))

        # Atomic commit: publish valid records and update quarantine records
        with transaction.atomic():
            if transformed_to_publish:
                Publisher.publish_batch(transformed_to_publish)

            if records_to_mark_replayed:
                QuarantineRecord.objects.bulk_update(
                    records_to_mark_replayed,
                    fields=['status', 'attempt_count', 'replayed_at', 'updated_at'],
                    batch_size=1000
                )

            if records_to_mark_failed:
                QuarantineRecord.objects.bulk_update(
                    records_to_mark_failed,
                    fields=['status', 'attempt_count', 'error_code', 'error_reason', 'validation_stage', 'validation_errors', 'updated_at'],
                    batch_size=1000
                )

        successful_count = len(successful_ids)
        failed_count = len(failed_records_info)

        # Update replay history
        replay_history.total_submitted = total_submitted
        replay_history.successful_count = successful_count
        replay_history.failed_count = failed_count
        replay_history.replayed_record_ids = successful_ids
        replay_history.status = 'COMPLETED'
        replay_history.completed_at = timezone.now()
        if failed_count > 0:
            replay_history.error_summary = f"{failed_count} records failed re-validation during replay."
        replay_history.save()

        remaining_pending = QuarantineRecord.objects.filter(status__in=['PENDING', 'CORRECTED', 'FAILED']).count()

        return {
            'replay_id': str(replay_history.replay_id),
            'total_submitted': total_submitted,
            'successful_count': successful_count,
            'failed_count': failed_count,
            'remaining_quarantine_count': remaining_pending,
            'status': 'COMPLETED',
            'successful_ids': successful_ids,
            'failed_records': failed_records_info,
        }

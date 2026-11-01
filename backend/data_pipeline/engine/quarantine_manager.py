"""
Quarantine Manager for Invalid Records.
Handles storing rejected records, multi-error tracking, operator corrections, and audit logging.
"""
import uuid
from typing import Dict, Any, List, Optional
from django.db import transaction
from apps.quarantine.models import QuarantineRecord, CorrectionHistory


class QuarantineManager:
    @classmethod
    def quarantine_batch(
        cls,
        invalid_items: List[Dict[str, Any]],
        run_id: str,
        source_file: str
    ) -> List[QuarantineRecord]:
        """
        Bulk inserts quarantined records.
        invalid_items format:
        [
            {
                'record': raw_record_dict,
                'row_number': int,
                'errors': [ {error_code, error_reason, validation_stage, field_name}, ... ]
            },
            ...
        ]
        """
        records_to_create = []

        for item in invalid_items:
            raw = item['record']
            row_num = item['row_number']
            errs = item['errors']

            primary_err = errs[0] if errs else {
                'error_code': 'ERR_UNKNOWN',
                'error_reason': 'Unknown validation error',
                'validation_stage': 'SYSTEM',
            }

            rec_id = str(raw.get('reading_id') or raw.get('record_id') or raw.get('order_id') or f"GEN-{uuid.uuid4().hex[:8]}")

            # Summarize all error reasons if multiple
            if len(errs) > 1:
                summary_reason = "; ".join([f"{e.get('field_name', 'field')}: {e['error_reason']}" for e in errs])
            else:
                summary_reason = primary_err['error_reason']

            records_to_create.append(
                QuarantineRecord(
                    record_id=rec_id,
                    source_file=source_file,
                    source_row_number=row_num,
                    run_id=run_id,
                    raw_record=raw,
                    error_code=primary_err['error_code'],
                    error_reason=summary_reason,
                    validation_stage=primary_err.get('validation_stage', 'SCHEMA'),
                    validation_errors=errs,
                    status='PENDING',
                    attempt_count=0,
                )
            )

        if records_to_create:
            created = QuarantineRecord.objects.bulk_create(records_to_create, batch_size=2000)
            return created
        return []

    @classmethod
    def apply_correction(
        cls,
        quarantine_id: str,
        corrected_payload: Dict[str, Any],
        operator_name: str = 'operator',
        notes: Optional[str] = None
    ) -> QuarantineRecord:
        """
        Applies an operator correction to a quarantined record.
        Transitions status from PENDING/FAILED to CORRECTED.
        Preserves complete history in correction_history.
        """
        with transaction.atomic():
            record = QuarantineRecord.objects.select_for_update().get(quarantine_id=quarantine_id)

            prev_payload = record.corrected_record or record.raw_record

            # Compute field diff
            changed_fields = {}
            for k, v in corrected_payload.items():
                prev_val = prev_payload.get(k)
                if str(prev_val) != str(v):
                    changed_fields[k] = {'old': prev_val, 'new': v}

            # Create audit history record
            CorrectionHistory.objects.create(
                quarantine_record=record,
                previous_payload=prev_payload,
                corrected_payload=corrected_payload,
                changed_fields=changed_fields,
                corrected_by=operator_name,
                correction_notes=notes or "Operator manual correction"
            )

            # Update quarantine record
            record.corrected_record = corrected_payload
            record.status = 'CORRECTED'
            record.save(update_fields=['corrected_record', 'status', 'updated_at'])

            return record

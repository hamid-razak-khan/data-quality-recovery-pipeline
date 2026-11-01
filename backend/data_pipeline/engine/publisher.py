"""
Publisher for Valid Records.
Publishes transformed records into PostgreSQL with atomic upsert idempotency.
"""
from typing import List, Dict, Any
from decimal import Decimal
from django.db import transaction
from apps.processing.models import ProcessedOrder


class Publisher:
    @classmethod
    def publish_batch(cls, transformed_records: List[Dict[str, Any]]) -> int:
        """
        Publishes a list of transformed record dictionaries into processed_orders.
        Uses PostgreSQL ON CONFLICT (order_id) DO UPDATE for strict idempotency.
        Returns the number of records published.
        """
        if not transformed_records:
            return 0

        instances = [
            ProcessedOrder(
                order_id=r.get('order_id') or r.get('record_id') or r.get('reading_id'),
                reading_id=r.get('reading_id'),
                asset_code=r.get('asset_code'),
                metric_name=r.get('metric_name'),
                metric_value=r.get('metric_value'),
                unit=r.get('unit'),
                observed_at=r.get('observed_at'),
                quality_flag=r.get('quality_flag'),
                customer_id=r.get('customer_id'),
                entity_id=r.get('entity_id') or r.get('asset_code') or r.get('customer_id'),
                event_type=r.get('event_type') or r.get('metric_name') or r.get('product_name'),
                amount=r.get('amount') if r.get('amount') is not None else (r.get('metric_value') if r.get('metric_value') is not None else r.get('total_amount')),
                quantity=r.get('quantity'),
                event_timestamp=r.get('event_timestamp') or r.get('observed_at') or r.get('order_date'),
                status=r.get('status') or r.get('quality_flag') or r.get('order_status'),
                product_name=r.get('product_name', ''),
                unit_price=r.get('unit_price') or r.get('amount') or Decimal('0.00'),
                total_amount=r.get('total_amount') or r.get('amount') or Decimal('0.00'),
                order_date=r.get('order_date') or r.get('observed_at') or r.get('event_timestamp'),
                order_status=r.get('order_status') or r.get('quality_flag') or r.get('status', 'ACTIVE'),
                source_file=r['source_file'],
                source_row_number=r['source_row_number'],
                run_id=r['run_id'],
                raw_payload=r.get('raw_payload'),
            )
            for r in transformed_records
        ]

        with transaction.atomic():
            ProcessedOrder.objects.bulk_create(
                instances,
                update_conflicts=True,
                unique_fields=['order_id'],
                update_fields=[
                    'reading_id',
                    'asset_code',
                    'metric_name',
                    'metric_value',
                    'unit',
                    'observed_at',
                    'quality_flag',
                    'customer_id',
                    'entity_id',
                    'event_type',
                    'amount',
                    'quantity',
                    'event_timestamp',
                    'status',
                    'product_name',
                    'unit_price',
                    'total_amount',
                    'order_date',
                    'order_status',
                    'source_file',
                    'source_row_number',
                    'run_id',
                    'raw_payload',
                    'updated_at',
                ],
                batch_size=2000
            )

        return len(instances)

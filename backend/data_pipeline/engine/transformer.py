"""
Transformation Engine for Valid Records.
Performs deterministic, standardized normalization:
1. Identifier normalization (whitespace trimming)
2. Status & event type standardization (uppercase)
3. ISO-8601 UTC datetime conversion
4. Exact financial Decimal precision
5. Source metadata attachment
"""
import re
from typing import Dict, Any, Optional, Union
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
import dateutil.parser

from data_pipeline.engine.schema_registry import SchemaRegistry, SchemaConfig


class Transformer:
    @classmethod
    def transform_record(
        cls,
        record: Dict[str, Any],
        schema: Optional[Union[SchemaConfig, str]] = None,
        run_id: str = "",
        source_file: str = "",
        source_row_number: int = 0
    ) -> Dict[str, Any]:
        """
        Transforms a validated raw record into canonical format.
        Preserves original values in source metadata.
        """
        if isinstance(schema, str):
            schema_obj = SchemaRegistry.get(schema)
        elif isinstance(schema, SchemaConfig):
            schema_obj = schema
        else:
            schema_obj = SchemaRegistry.detect_schema(record)

        if schema_obj and schema_obj.name == 'generic':
            return cls._transform_generic(record, run_id, source_file, source_row_number)
        elif schema_obj and schema_obj.name == 'telemetry':
            return cls._transform_telemetry(record, run_id, source_file, source_row_number)
        else:
            return cls._transform_ecommerce(record, run_id, source_file, source_row_number)

    @classmethod
    def _transform_generic(
        cls,
        record: Dict[str, Any],
        run_id: str,
        source_file: str,
        source_row_number: int
    ) -> Dict[str, Any]:
        record_id = str(record['record_id']).strip()
        entity_id = str(record['entity_id']).strip()
        event_type = str(record['event_type']).strip().upper()
        amount = Decimal(str(record['amount'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        quantity = int(str(record['quantity']).strip())
        event_timestamp = cls._to_utc_datetime(record['event_timestamp'])
        status = str(record['status']).strip().upper()

        return {
            'record_id': record_id,
            'order_id': record_id,
            'entity_id': entity_id,
            'event_type': event_type,
            'amount': amount,
            'quantity': quantity,
            'event_timestamp': event_timestamp,
            'status': status,
            # Dual-compatibility fields for target store
            'customer_id': None,
            'product_name': event_type,
            'unit_price': amount,
            'total_amount': amount,
            'order_date': event_timestamp,
            'order_status': status,
            'source_file': source_file,
            'source_row_number': source_row_number,
            'run_id': run_id,
            'raw_payload': record,
        }

    @classmethod
    def _transform_telemetry(
        cls,
        record: Dict[str, Any],
        run_id: str,
        source_file: str,
        source_row_number: int
    ) -> Dict[str, Any]:
        reading_id = str(record['reading_id']).strip()
        asset_code = str(record['asset_code']).strip()
        metric_name = str(record['metric_name']).strip().lower()
        metric_value = Decimal(str(record['metric_value'])).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
        unit = str(record['unit']).strip()
        observed_at = cls._to_utc_datetime(record['observed_at'])
        quality_flag = str(record['quality_flag']).strip().upper()

        return {
            'order_id': reading_id,
            'reading_id': reading_id,
            'record_id': reading_id,
            'asset_code': asset_code,
            'entity_id': asset_code,
            'metric_name': metric_name,
            'event_type': metric_name,
            'metric_value': metric_value,
            'amount': metric_value,
            'unit': unit,
            'observed_at': observed_at,
            'event_timestamp': observed_at,
            'quality_flag': quality_flag,
            'status': quality_flag,
            'order_status': quality_flag,
            'customer_id': None,
            'product_name': metric_name,
            'unit_price': metric_value,
            'total_amount': metric_value,
            'quantity': 1,
            'order_date': observed_at,
            'source_file': source_file,
            'source_row_number': source_row_number,
            'run_id': run_id,
            'raw_payload': record,
        }

    @classmethod
    def _transform_ecommerce(
        cls,
        record: Dict[str, Any],
        run_id: str,
        source_file: str,
        source_row_number: int
    ) -> Dict[str, Any]:
        order_id = str(record['order_id']).strip()
        customer_id = str(record['customer_id']).strip()
        raw_product = str(record.get('product_name', '')).strip()
        product_name = re.sub(r'\s+', ' ', raw_product)
        order_status = str(record.get('order_status', '')).strip().upper()

        quantity = int(str(record['quantity']).strip())
        unit_price = Decimal(str(record['unit_price'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        total_amount = Decimal(str(record['total_amount'])).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        order_date_dt = cls._to_utc_datetime(record['order_date'])

        return {
            'record_id': order_id,
            'order_id': order_id,
            'customer_id': customer_id,
            'entity_id': customer_id,
            'event_type': 'ORDER',
            'amount': total_amount,
            'product_name': product_name,
            'quantity': quantity,
            'unit_price': unit_price,
            'total_amount': total_amount,
            'order_date': order_date_dt,
            'event_timestamp': order_date_dt,
            'order_status': order_status,
            'status': order_status,
            'source_file': source_file,
            'source_row_number': source_row_number,
            'run_id': run_id,
            'raw_payload': record,
        }

    @staticmethod
    def _to_utc_datetime(raw_date: Any) -> datetime:
        if isinstance(raw_date, datetime):
            if raw_date.tzinfo is None:
                return raw_date.replace(tzinfo=timezone.utc)
            return raw_date.astimezone(timezone.utc)

        date_str = str(raw_date).strip()
        # Parse using dateutil for flexible timezone and format handling
        dt = dateutil.parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt

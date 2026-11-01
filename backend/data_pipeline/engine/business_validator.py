"""
Configurable Business Validator.
Enforces domain business rules based on the active schema configuration:
1. Numerical boundary enforcement (quantities > 0, amounts >= 0, prices > 0)
2. Allowed enumeration values (statuses, event types)
3. Date range validity (2000 - 2100)
4. Schema-specific cross-field rules (e.g. FK checks, total amount calculation)
"""
from typing import Dict, Any, List, Set, Tuple, Optional, Union
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from datetime import datetime

from data_pipeline.engine.schema_registry import (
    SchemaRegistry,
    SchemaConfig,
    _is_valid_date_string,
)


class BusinessValidator:
    @classmethod
    def validate_record(
        cls,
        record: Dict[str, Any],
        schema: Optional[Union[SchemaConfig, str]] = None,
        valid_customer_ids: Optional[Set[str]] = None,
        source_file: str = "",
        source_row_number: int = 0
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validates business rules for a single record according to its configured schema.
        Assumes schema validation has passed (required fields exist and are convertible).
        """
        if isinstance(schema, str):
            schema_obj = SchemaRegistry.get(schema)
        elif isinstance(schema, SchemaConfig):
            schema_obj = schema
        else:
            schema_obj = SchemaRegistry.detect_schema(record)

        if schema_obj is None:
            schema_obj = SchemaRegistry.get('generic')

        errors = []

        if schema_obj.name == 'generic':
            cls._validate_generic(record, errors, source_file, source_row_number)
        elif schema_obj.name == 'telemetry':
            cls._validate_telemetry(record, errors, source_file, source_row_number)
        else:
            cls._validate_ecommerce(record, errors, valid_customer_ids, source_file, source_row_number)

        # Execute any custom cross-field validator defined in schema
        if schema_obj.cross_field_validator:
            context = {'valid_customer_ids': valid_customer_ids}
            cross_errors = schema_obj.cross_field_validator(record, context)
            for ce in cross_errors:
                ce.setdefault('source_file', source_file)
                ce.setdefault('source_row_number', source_row_number)
                errors.append(ce)

        is_valid = len(errors) == 0
        return is_valid, errors

    @classmethod
    def _validate_generic(
        cls,
        record: Dict[str, Any],
        errors: List[Dict[str, Any]],
        source_file: str,
        source_row_number: int
    ):
        # 1. Quantity must be a positive integer (> 0)
        try:
            qty = int(str(record.get('quantity', 0)).strip())
            if qty <= 0:
                errors.append({
                    'error_code': 'ERR_INVALID_QUANTITY',
                    'error_reason': f"Quantity must be greater than zero. Received: {qty}.",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'quantity',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })
        except (ValueError, TypeError):
            errors.append({
                'error_code': 'ERR_INVALID_QUANTITY',
                'error_reason': "Invalid quantity value.",
                'validation_stage': 'BUSINESS',
                'field_name': 'quantity',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })

        # 2. Amount must be valid numeric >= 0.00
        try:
            amt = Decimal(str(record.get('amount', '0')).strip())
            if amt < Decimal('0.00'):
                errors.append({
                    'error_code': 'ERR_INVALID_PRICE',
                    'error_reason': f"Amount must be greater than or equal to zero. Received: {amt}.",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'amount',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })
        except Exception:
            errors.append({
                'error_code': 'ERR_INVALID_PRICE',
                'error_reason': "Invalid amount value.",
                'validation_stage': 'BUSINESS',
                'field_name': 'amount',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })

        # 3. Event Type must be one of {CREATED, UPDATED, COMPLETED, CANCELLED}
        allowed_events = {'CREATED', 'UPDATED', 'COMPLETED', 'CANCELLED'}
        raw_event = str(record.get('event_type', '')).strip().upper()
        if raw_event not in allowed_events:
            errors.append({
                'error_code': 'ERR_INVALID_STATUS',
                'error_reason': (
                    f"Event type '{record.get('event_type')}' is invalid. "
                    f"Allowed: {', '.join(sorted(allowed_events))}."
                ),
                'validation_stage': 'BUSINESS',
                'field_name': 'event_type',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })

        # 4. Status must be one of {ACTIVE, COMPLETED, CANCELLED}
        allowed_statuses = {'ACTIVE', 'COMPLETED', 'CANCELLED'}
        raw_status = str(record.get('status', '')).strip().upper()
        if raw_status not in allowed_statuses:
            errors.append({
                'error_code': 'ERR_INVALID_STATUS',
                'error_reason': (
                    f"Status '{record.get('status')}' is invalid. "
                    f"Allowed statuses: {', '.join(sorted(allowed_statuses))}."
                ),
                'validation_stage': 'BUSINESS',
                'field_name': 'status',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })

        # 5. Event Timestamp range check (2000-2100)
        raw_ts = record.get('event_timestamp')
        parsed_dt = cls._parse_iso_date(raw_ts)
        if parsed_dt is not None:
            if parsed_dt.year < 2000 or parsed_dt.year > 2100:
                errors.append({
                    'error_code': 'ERR_INVALID_DATE_RANGE',
                    'error_reason': f"Event timestamp '{raw_ts}' is outside allowable range (2000-2100).",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'event_timestamp',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })

    @classmethod
    def _validate_telemetry(
        cls,
        record: Dict[str, Any],
        errors: List[Dict[str, Any]],
        source_file: str,
        source_row_number: int
    ):
        METRIC_CONFIG = {
            'temperature': {
                'units': {'c', '°c'},
                'min_val': Decimal('-40.0'),
                'max_val': Decimal('150.0'),
                'expected_unit': 'C',
            },
            'humidity': {
                'units': {'%'},
                'min_val': Decimal('0.0'),
                'max_val': Decimal('100.0'),
                'expected_unit': '%',
            },
            'pressure': {
                'units': {'kpa'},
                'min_val': Decimal('0.0'),
                'max_val': None,
                'expected_unit': 'kPa',
            },
            'vibration': {
                'units': {'mm/s'},
                'min_val': Decimal('0.0'),
                'max_val': None,
                'expected_unit': 'mm/s',
            },
        }

        raw_metric = str(record.get('metric_name', '')).strip().lower()
        if raw_metric not in METRIC_CONFIG:
            errors.append({
                'error_code': 'ERR_INVALID_METRIC_NAME',
                'error_reason': (
                    f"Metric name '{record.get('metric_name')}' is invalid. "
                    f"Allowed metrics: {', '.join(sorted(METRIC_CONFIG.keys()))}."
                ),
                'validation_stage': 'BUSINESS',
                'field_name': 'metric_name',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })
            return

        metric_cfg = METRIC_CONFIG[raw_metric]

        # 1. Metric Unit Validation
        raw_unit = str(record.get('unit', '')).strip()
        if raw_unit.lower() not in metric_cfg['units']:
            errors.append({
                'error_code': 'ERR_INVALID_UNIT',
                'error_reason': (
                    f"Invalid unit '{raw_unit}' for metric '{raw_metric}'. "
                    f"Expected '{metric_cfg['expected_unit']}'."
                ),
                'validation_stage': 'BUSINESS',
                'field_name': 'unit',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })

        # 2. Metric Value Boundaries
        raw_val = record.get('metric_value')
        try:
            val = Decimal(str(raw_val).strip())
            min_v = metric_cfg['min_val']
            max_v = metric_cfg['max_val']
            if min_v is not None and val < min_v:
                errors.append({
                    'error_code': 'ERR_INVALID_BOUNDARY',
                    'error_reason': f"Metric value {val} is below allowable minimum of {min_v} for {raw_metric}.",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'metric_value',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })
            elif max_v is not None and val > max_v:
                errors.append({
                    'error_code': 'ERR_INVALID_BOUNDARY',
                    'error_reason': f"Metric value {val} exceeds allowable maximum of {max_v} for {raw_metric}.",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'metric_value',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })
        except Exception:
            errors.append({
                'error_code': 'ERR_INVALID_TYPE',
                'error_reason': f"Metric value '{raw_val}' is not a valid numeric value.",
                'validation_stage': 'BUSINESS',
                'field_name': 'metric_value',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })

        # 3. Quality Flag Validation
        allowed_flags = {'GOOD', 'REVIEW'}
        raw_flag = str(record.get('quality_flag', '')).strip().upper()
        if raw_flag not in allowed_flags:
            errors.append({
                'error_code': 'ERR_INVALID_STATUS',
                'error_reason': (
                    f"Quality flag '{record.get('quality_flag')}' is invalid. "
                    f"Allowed: {', '.join(sorted(allowed_flags))}."
                ),
                'validation_stage': 'BUSINESS',
                'field_name': 'quality_flag',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })

        # 4. Observed At range check (2000-2100)
        raw_ts = record.get('observed_at')
        parsed_dt = cls._parse_iso_date(raw_ts)
        if parsed_dt is not None:
            if parsed_dt.year < 2000 or parsed_dt.year > 2100:
                errors.append({
                    'error_code': 'ERR_INVALID_DATE_RANGE',
                    'error_reason': f"Observed timestamp '{raw_ts}' is outside allowable range (2000-2100).",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'observed_at',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })

    @classmethod
    def _validate_ecommerce(
        cls,
        record: Dict[str, Any],
        errors: List[Dict[str, Any]],
        valid_customer_ids: Optional[Set[str]],
        source_file: str,
        source_row_number: int
    ):
        # 1. Foreign Key Validation (Customer existence)
        cust_id = str(record.get('customer_id', '')).strip()
        if valid_customer_ids is not None:
            if cust_id not in valid_customer_ids:
                errors.append({
                    'error_code': 'ERR_INVALID_FK',
                    'error_reason': f"Customer ID '{cust_id}' does not exist in customers master table.",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'customer_id',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })

        # 2. Positive Quantity (> 0)
        try:
            qty = int(record.get('quantity', 0))
            if qty <= 0:
                errors.append({
                    'error_code': 'ERR_INVALID_QUANTITY',
                    'error_reason': f"Quantity must be greater than zero. Received: {qty}.",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'quantity',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })
        except (ValueError, TypeError):
            errors.append({
                'error_code': 'ERR_INVALID_QUANTITY',
                'error_reason': "Invalid quantity value.",
                'validation_stage': 'BUSINESS',
                'field_name': 'quantity',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })
            qty = 0

        # 3. Positive Unit Price (> 0.00)
        try:
            unit_price = Decimal(str(record.get('unit_price', '0')).strip())
            if unit_price <= Decimal('0.00'):
                errors.append({
                    'error_code': 'ERR_INVALID_PRICE',
                    'error_reason': f"Unit price must be positive. Received: {unit_price}.",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'unit_price',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })
        except Exception:
            errors.append({
                'error_code': 'ERR_INVALID_PRICE',
                'error_reason': "Invalid unit price value.",
                'validation_stage': 'BUSINESS',
                'field_name': 'unit_price',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })
            unit_price = Decimal('0.00')

        # 4. Calculation Integrity: total_amount == round(quantity * unit_price, 2)
        try:
            total_amount = Decimal(str(record.get('total_amount', '0')).strip())
            if qty > 0 and unit_price > Decimal('0.00'):
                expected_total = (Decimal(qty) * unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                given_total = total_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if expected_total != given_total:
                    errors.append({
                        'error_code': 'ERR_CALCULATION_MISMATCH',
                        'error_reason': (
                            f"Total amount mismatch: expected {expected_total} "
                            f"(quantity {qty} * price {unit_price}), but received {given_total}."
                        ),
                        'validation_stage': 'BUSINESS',
                        'field_name': 'total_amount',
                        'source_file': source_file,
                        'source_row_number': source_row_number,
                    })
        except Exception:
            errors.append({
                'error_code': 'ERR_CALCULATION_MISMATCH',
                'error_reason': "Could not calculate or parse total amount.",
                'validation_stage': 'BUSINESS',
                'field_name': 'total_amount',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })

        # 5. Order Status Validation
        allowed_statuses = {'PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED'}
        raw_status = str(record.get('order_status', '')).strip().upper()
        if raw_status not in allowed_statuses:
            errors.append({
                'error_code': 'ERR_INVALID_STATUS',
                'error_reason': (
                    f"Order status '{record.get('order_status')}' is invalid. "
                    f"Allowed statuses: {', '.join(sorted(allowed_statuses))}."
                ),
                'validation_stage': 'BUSINESS',
                'field_name': 'order_status',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })

        # 6. Date Validity (2000-2100)
        raw_date = record.get('order_date')
        parsed_dt = cls._parse_iso_date(raw_date)
        if parsed_dt is None:
            errors.append({
                'error_code': 'ERR_INVALID_DATE',
                'error_reason': f"Order date '{raw_date}' could not be parsed as valid date.",
                'validation_stage': 'BUSINESS',
                'field_name': 'order_date',
                'source_file': source_file,
                'source_row_number': source_row_number,
            })
        else:
            if parsed_dt.year < 2000 or parsed_dt.year > 2100:
                errors.append({
                    'error_code': 'ERR_INVALID_DATE_RANGE',
                    'error_reason': f"Order date '{raw_date}' is outside allowable range (2000-2100).",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'order_date',
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })

    @staticmethod
    def _parse_iso_date(date_val: Any) -> Optional[datetime]:
        if not date_val:
            return None
        date_str = str(date_val).strip().replace('Z', '+00:00')
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            pass

        formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S%z",
            "%d/%m/%Y",
            "%m/%d/%Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

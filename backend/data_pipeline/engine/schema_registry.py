"""
Configurable Schema Registry and Definitions.
Allows registering domain-specific schemas without hardcoding assumptions in the core engine.
"""
from typing import Dict, Any, List, Set, Optional, Callable, Union, Tuple
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone
import re


class ColumnRule:
    def __init__(
        self,
        name: str,
        required: bool = True,
        allow_null: bool = False,
        data_type: str = 'string',  # 'string', 'integer', 'decimal', 'timestamp'
        min_value: Optional[Union[Decimal, int, float]] = None,
        max_value: Optional[Union[Decimal, int, float]] = None,
        allowed_values: Optional[Set[str]] = None,
        custom_validator: Optional[Callable[[Any, Dict[str, Any]], Tuple[bool, Optional[str]]]] = None,
    ):
        self.name = name
        self.required = required
        self.allow_null = allow_null
        self.data_type = data_type
        self.min_value = min_value
        self.max_value = max_value
        self.allowed_values = {v.upper() for v in allowed_values} if allowed_values else None
        self.custom_validator = custom_validator


class SchemaConfig:
    def __init__(
        self,
        name: str,
        id_column: str,
        required_columns: List[str],
        column_rules: Dict[str, ColumnRule],
        description: str = "",
        cross_field_validator: Optional[Callable[[Dict[str, Any], Dict[str, Any]], List[Dict[str, Any]]]] = None,
    ):
        self.name = name
        self.id_column = id_column
        self.required_columns = required_columns
        self.column_rules = column_rules
        self.description = description
        self.cross_field_validator = cross_field_validator


def _is_valid_timestamp_string(val: Any) -> bool:
    """
    Validates that a string is a parseable timestamp with both date and time components.
    Strings like '31/10/2026' or 'not-a-timestamp' without time are rejected.
    """
    if not val:
        return False
    val_str = str(val).strip()
    # Timestamps in streaming/pipelines should have time component (e.g. contains 'T' or ' ' with ':')
    # Reject strings with no time components or known malformed formats
    if ':' not in val_str:
        return False

    val_iso = val_str.replace('Z', '+00:00')
    try:
        dt = datetime.fromisoformat(val_iso)
        return True
    except (ValueError, TypeError):
        pass

    common_formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ]
    for fmt in common_formats:
        try:
            datetime.strptime(val_str, fmt)
            return True
        except (ValueError, TypeError):
            continue
    return False


def _is_valid_date_string(val: Any) -> bool:
    """Validates that a string is parseable as a date or datetime."""
    if not val:
        return False
    val_str = str(val).strip().replace('Z', '+00:00')
    try:
        datetime.fromisoformat(val_str)
        return True
    except (ValueError, TypeError):
        pass

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S%z",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            datetime.strptime(val_str, fmt)
            return True
        except (ValueError, TypeError):
            continue
    return False


class SchemaRegistry:
    _schemas: Dict[str, SchemaConfig] = {}

    @classmethod
    def register(cls, schema: SchemaConfig):
        cls._schemas[schema.name.lower()] = schema

    @classmethod
    def get(cls, name: str) -> Optional[SchemaConfig]:
        if not name:
            return None
        return cls._schemas.get(name.lower())

    @classmethod
    def detect_schema(cls, record_or_headers: Union[List[str], Dict[str, Any], Set[str]]) -> SchemaConfig:
        """
        Detects the best matching schema based on column headers or record keys.
        Falls back to 'generic' if columns match generic fields, else 'ecommerce'.
        """
        if isinstance(record_or_headers, dict):
            keys = set(record_or_headers.keys())
        elif isinstance(record_or_headers, (list, tuple, set)):
            keys = set(record_or_headers)
        else:
            return cls._schemas.get('generic') or list(cls._schemas.values())[0]

        best_schema = None
        best_score = -1

        for schema in cls._schemas.values():
            req_set = set(schema.required_columns)
            common = len(req_set.intersection(keys))
            has_id = schema.id_column in keys
            score = common + (5 if has_id else 0)
            if score > best_score:
                best_score = score
                best_schema = schema

        return best_schema or cls._schemas.get('generic')


# ---------------------------------------------------------------------------
# Pre-register built-in schemas
# ---------------------------------------------------------------------------

# 1. Generic Event Dataset Schema
GENERIC_SCHEMA = SchemaConfig(
    name='generic',
    id_column='record_id',
    required_columns=[
        'record_id',
        'entity_id',
        'event_type',
        'amount',
        'quantity',
        'event_timestamp',
        'status',
    ],
    column_rules={
        'record_id': ColumnRule(
            name='record_id',
            required=True,
            allow_null=False,
            data_type='string',
        ),
        'entity_id': ColumnRule(
            name='entity_id',
            required=True,
            allow_null=False,
            data_type='string',
        ),
        'event_type': ColumnRule(
            name='event_type',
            required=True,
            allow_null=False,
            data_type='string',
            allowed_values={'CREATED', 'UPDATED', 'COMPLETED', 'CANCELLED'},
        ),
        'amount': ColumnRule(
            name='amount',
            required=True,
            allow_null=False,
            data_type='decimal',
            min_value=Decimal('0.00'),
        ),
        'quantity': ColumnRule(
            name='quantity',
            required=True,
            allow_null=False,
            data_type='integer',
            min_value=1,  # Positive integer
        ),
        'event_timestamp': ColumnRule(
            name='event_timestamp',
            required=True,
            allow_null=False,
            data_type='timestamp',
        ),
        'status': ColumnRule(
            name='status',
            required=True,
            allow_null=False,
            data_type='string',
            allowed_values={'ACTIVE', 'COMPLETED', 'CANCELLED'},
        ),
    },
    description="Generic Event Pipeline dataset schema (record_id, entity_id, event_type, amount, quantity, event_timestamp, status)",
)

# 2. E-Commerce Order Dataset Schema
def _validate_ecommerce_cross_field(record: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    errors = []
    # Foreign key check for customer
    valid_customer_ids = context.get('valid_customer_ids')
    cust_id = str(record.get('customer_id', '')).strip()
    if valid_customer_ids is not None and cust_id not in valid_customer_ids:
        errors.append({
            'error_code': 'ERR_INVALID_FK',
            'error_reason': f"Customer ID '{cust_id}' does not exist in customers master table.",
            'validation_stage': 'BUSINESS',
            'field_name': 'customer_id',
        })

    # Calculation integrity: total_amount == round(quantity * unit_price, 2)
    try:
        raw_qty = record.get('quantity')
        raw_price = record.get('unit_price')
        raw_total = record.get('total_amount')
        qty = int(raw_qty)
        price = Decimal(str(raw_price).strip())
        total = Decimal(str(raw_total).strip())
        if qty > 0 and price > Decimal('0.00'):
            expected = (Decimal(qty) * price).quantize(Decimal('0.01'))
            given = total.quantize(Decimal('0.01'))
            if expected != given:
                errors.append({
                    'error_code': 'ERR_CALCULATION_MISMATCH',
                    'error_reason': f"Total amount mismatch: expected {expected} (quantity {qty} * price {price}), but received {given}.",
                    'validation_stage': 'BUSINESS',
                    'field_name': 'total_amount',
                })
    except Exception:
        pass

    return errors


ECOMMERCE_SCHEMA = SchemaConfig(
    name='ecommerce',
    id_column='order_id',
    required_columns=[
        'order_id',
        'customer_id',
        'product_name',
        'quantity',
        'unit_price',
        'total_amount',
        'order_date',
        'order_status',
    ],
    column_rules={
        'order_id': ColumnRule(
            name='order_id',
            required=True,
            allow_null=False,
            data_type='string',
        ),
        'customer_id': ColumnRule(
            name='customer_id',
            required=True,
            allow_null=False,
            data_type='string',
        ),
        'product_name': ColumnRule(
            name='product_name',
            required=True,
            allow_null=False,
            data_type='string',
        ),
        'quantity': ColumnRule(
            name='quantity',
            required=True,
            allow_null=False,
            data_type='integer',
            min_value=1,
        ),
        'unit_price': ColumnRule(
            name='unit_price',
            required=True,
            allow_null=False,
            data_type='decimal',
            min_value=Decimal('0.01'),
        ),
        'total_amount': ColumnRule(
            name='total_amount',
            required=True,
            allow_null=False,
            data_type='decimal',
        ),
        'order_date': ColumnRule(
            name='order_date',
            required=True,
            allow_null=False,
            data_type='date',
        ),
        'order_status': ColumnRule(
            name='order_status',
            required=True,
            allow_null=False,
            data_type='string',
            allowed_values={'PENDING', 'CONFIRMED', 'SHIPPED', 'DELIVERED', 'CANCELLED'},
        ),
    },
    description="E-commerce Orders schema (order_id, customer_id, product_name, quantity, unit_price, total_amount, order_date, order_status)",
    cross_field_validator=_validate_ecommerce_cross_field,
)

# 3. Asset Telemetry Dataset Schema
TELEMETRY_SCHEMA = SchemaConfig(
    name='telemetry',
    id_column='reading_id',
    required_columns=[
        'reading_id',
        'asset_code',
        'metric_name',
        'metric_value',
        'unit',
        'observed_at',
        'quality_flag',
    ],
    column_rules={
        'reading_id': ColumnRule(
            name='reading_id',
            required=True,
            allow_null=False,
            data_type='string',
        ),
        'asset_code': ColumnRule(
            name='asset_code',
            required=True,
            allow_null=False,
            data_type='string',
        ),
        'metric_name': ColumnRule(
            name='metric_name',
            required=True,
            allow_null=False,
            data_type='string',
            allowed_values={'TEMPERATURE', 'HUMIDITY', 'PRESSURE', 'VIBRATION'},
        ),
        'metric_value': ColumnRule(
            name='metric_value',
            required=True,
            allow_null=False,
            data_type='decimal',
        ),
        'unit': ColumnRule(
            name='unit',
            required=True,
            allow_null=False,
            data_type='string',
        ),
        'observed_at': ColumnRule(
            name='observed_at',
            required=True,
            allow_null=False,
            data_type='timestamp',
        ),
        'quality_flag': ColumnRule(
            name='quality_flag',
            required=True,
            allow_null=False,
            data_type='string',
            allowed_values={'GOOD', 'REVIEW'},
        ),
    },
    description="Asset Telemetry schema (reading_id, asset_code, metric_name, metric_value, unit, observed_at, quality_flag)",
)

SchemaRegistry.register(GENERIC_SCHEMA)
SchemaRegistry.register(ECOMMERCE_SCHEMA)
SchemaRegistry.register(TELEMETRY_SCHEMA)

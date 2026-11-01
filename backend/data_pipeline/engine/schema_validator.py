"""
Configurable Schema Validator.
Validates required columns, nullability, missing fields, and basic data types
against configured schemas without domain-specific assumptions.
"""
from typing import Dict, Any, List, Tuple, Optional, Union
from decimal import Decimal, InvalidOperation
from datetime import datetime

from data_pipeline.engine.schema_registry import (
    SchemaRegistry,
    SchemaConfig,
    _is_valid_timestamp_string,
    _is_valid_date_string,
)


class SchemaValidator:
    @classmethod
    def validate_record(
        cls,
        record: Dict[str, Any],
        schema: Optional[Union[SchemaConfig, str]] = None,
        source_file: str = "",
        source_row_number: int = 0
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Validates a single record against schema rules.
        If schema is not provided, auto-detects from the record keys.

        Returns:
            is_valid (bool): True if schema validation passed
            errors (list): List of error dictionaries
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

        # 1. Check for missing required keys or null/empty values
        for col in schema_obj.required_columns:
            rule = schema_obj.column_rules.get(col)
            if col not in record:
                errors.append({
                    'error_code': 'ERR_MISSING_FIELD',
                    'error_reason': f"Required column '{col}' is missing from record.",
                    'validation_stage': 'SCHEMA',
                    'field_name': col,
                    'source_file': source_file,
                    'source_row_number': source_row_number,
                })
            else:
                val = record[col]
                allow_null = rule.allow_null if rule else False
                if not allow_null:
                    if val is None or (isinstance(val, str) and val.strip() == ""):
                        errors.append({
                            'error_code': 'ERR_NULL_VALUE',
                            'error_reason': f"Column '{col}' must not be null or empty.",
                            'validation_stage': 'SCHEMA',
                            'field_name': col,
                            'source_file': source_file,
                            'source_row_number': source_row_number,
                        })

        # If mandatory columns are missing or null, don't attempt deep type checks
        if errors:
            return False, errors

        # 2. Data Type & Format Validations
        for col, rule in schema_obj.column_rules.items():
            if col not in record:
                continue
            val = record[col]
            if val is None or (isinstance(val, str) and val.strip() == ""):
                continue
            val_str = str(val).strip()

            # Integer validation
            if rule.data_type == 'integer':
                try:
                    int(val_str)
                except (ValueError, TypeError):
                    errors.append({
                        'error_code': 'ERR_INVALID_TYPE',
                        'error_reason': (
                            f"Quantity '{val}' is not a valid integer."
                            if col == 'quantity'
                            else f"Column '{col}' value '{val}' is not a valid integer."
                        ),
                        'validation_stage': 'SCHEMA',
                        'field_name': col,
                        'source_file': source_file,
                        'source_row_number': source_row_number,
                    })

            # Decimal / Numeric validation
            elif rule.data_type == 'decimal':
                try:
                    Decimal(val_str)
                except (InvalidOperation, TypeError, ValueError):
                    if col == 'amount':
                        reason = f"Amount '{val}' is not a valid numeric value."
                    elif col == 'unit_price':
                        reason = f"Unit price '{val}' is not a valid decimal number."
                    elif col == 'total_amount':
                        reason = f"Total amount '{val}' is not a valid decimal number."
                    else:
                        reason = f"Column '{col}' value '{val}' is not a valid decimal number."

                    errors.append({
                        'error_code': 'ERR_INVALID_TYPE',
                        'error_reason': reason,
                        'validation_stage': 'SCHEMA',
                        'field_name': col,
                        'source_file': source_file,
                        'source_row_number': source_row_number,
                    })

            # Timestamp validation (requires date and time)
            elif rule.data_type == 'timestamp':
                if not _is_valid_timestamp_string(val):
                    errors.append({
                        'error_code': 'ERR_INVALID_DATE_FORMAT',
                        'error_reason': (
                            f"Event timestamp '{val}' is not a valid timestamp."
                            if col == 'event_timestamp'
                            else f"Column '{col}' value '{val}' is not a valid timestamp."
                        ),
                        'validation_stage': 'SCHEMA',
                        'field_name': col,
                        'source_file': source_file,
                        'source_row_number': source_row_number,
                    })

            # Date validation (date or datetime)
            elif rule.data_type == 'date':
                if not _is_valid_date_string(val):
                    errors.append({
                        'error_code': 'ERR_INVALID_DATE_FORMAT',
                        'error_reason': (
                            f"Order date '{val}' is not a valid parseable date."
                            if col == 'order_date'
                            else f"Column '{col}' value '{val}' is not a valid date."
                        ),
                        'validation_stage': 'SCHEMA',
                        'field_name': col,
                        'source_file': source_file,
                        'source_row_number': source_row_number,
                    })

        is_valid = len(errors) == 0
        return is_valid, errors

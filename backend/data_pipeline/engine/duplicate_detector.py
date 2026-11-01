"""
Duplicate Detector for Incoming Records.
Detects duplicates within incoming batches and tracks existing business keys
based on the active schema's unique record identifier (e.g. record_id or order_id).
"""
from typing import Dict, Any, List, Set, Tuple, Optional, Union
from data_pipeline.engine.schema_registry import SchemaRegistry, SchemaConfig


class DuplicateDetector:
    def __init__(self, id_column: str = 'record_id', existing_ids: Optional[Set[str]] = None):
        """
        Args:
            id_column: Primary identifier column to track for uniqueness.
            existing_ids: Set of business keys already stored in the target DB (optional).
        """
        self.id_column = id_column
        self.seen_batch_ids: Set[str] = set()
        self.existing_ids: Set[str] = existing_ids or set()

    def check_duplicate(
        self,
        record: Dict[str, Any],
        schema: Optional[Union[SchemaConfig, str]] = None,
        source_file: str = "",
        source_row_number: int = 0
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Checks if the record's primary identifier is a duplicate within the current batch.
        Returns:
            is_duplicate (bool): True if duplicate
            errors (list): List of error dictionaries if duplicate
        """
        if isinstance(schema, str):
            schema_obj = SchemaRegistry.get(schema)
        elif isinstance(schema, SchemaConfig):
            schema_obj = schema
        else:
            schema_obj = None

        col = schema_obj.id_column if schema_obj else self.id_column

        # Fallback inspection if column not present in record
        raw_id = record.get(col)
        if raw_id is None or (isinstance(raw_id, str) and not raw_id.strip()):
            for fallback_col in ('reading_id', 'record_id', 'order_id'):
                if fallback_col in record and record[fallback_col] and str(record[fallback_col]).strip():
                    col = fallback_col
                    raw_id = record[col]
                    break

        if raw_id is None or (isinstance(raw_id, str) and not raw_id.strip()):
            # Missing ID is caught by schema validator
            return False, []

        rec_id = str(raw_id).strip()

        # Check duplicate within the batch
        if rec_id in self.seen_batch_ids:
            err_code = 'ERR_DUPLICATE_ORDER_ID' if col == 'order_id' else 'ERR_DUPLICATE_RECORD_ID'
            return True, [{
                'error_code': err_code,
                'error_reason': f"Duplicate {col} '{rec_id}' found in current batch (already seen in row).",
                'validation_stage': 'BUSINESS',
                'field_name': col,
                'source_file': source_file,
                'source_row_number': source_row_number,
            }]

        self.seen_batch_ids.add(rec_id)
        return False, []

    def reset_batch(self):
        """Resets the in-batch tracking set."""
        self.seen_batch_ids.clear()

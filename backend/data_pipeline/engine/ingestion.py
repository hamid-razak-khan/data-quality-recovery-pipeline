"""
Data Ingestion Pipeline Engine.
Orchestrates:
1. File validation & SHA-256 fingerprinting
2. Batch/Stream reading of CSV and JSON files
3. Dynamic schema detection from headers or configured schema
4. Duplicate detection using active schema identifier
5. Configurable schema validation
6. Configurable business validation
7. Transformation & PostgreSQL upsert publishing
8. Quarantine routing with multi-error tracking
9. Pipeline run tracking & reconciliation metrics
"""
import os
import sys
import time
import uuid
import hashlib
import json
import logging
import csv
from typing import Dict, Any, List, Optional
import pandas as pd
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.ingestion.models import SourceFile, PipelineRun, SourceRecord
from apps.processing.models import Customer, ProcessedOrder
from data_pipeline.engine.schema_registry import SchemaRegistry, SchemaConfig
from data_pipeline.engine.schema_validator import SchemaValidator
from data_pipeline.engine.business_validator import BusinessValidator
from data_pipeline.engine.duplicate_detector import DuplicateDetector
from data_pipeline.engine.transformer import Transformer
from data_pipeline.engine.publisher import Publisher
from data_pipeline.engine.quarantine_manager import QuarantineManager

logger = logging.getLogger('pipeline')


class IngestionEngine:
    BATCH_SIZE = 5000

    @classmethod
    def calculate_file_hash(cls, file_path: str) -> str:
        """Calculates SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def _detect_file_schema(cls, file_path: str, file_ext: str, schema_name: Optional[str] = None) -> SchemaConfig:
        """Detects schema from configured schema_name or by inspecting file headers."""
        if schema_name:
            cfg = SchemaRegistry.get(schema_name)
            if cfg:
                return cfg

        headers: List[str] = []
        try:
            if file_ext == '.csv':
                with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        headers = [col.strip() for col in row if col.strip()]
                        break
            elif file_ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_char = f.read(1)
                    f.seek(0)
                    if first_char == '[':
                        data = json.load(f)
                        if data and isinstance(data, list) and isinstance(data[0], dict):
                            headers = list(data[0].keys())
                    else:
                        line = f.readline().strip()
                        if line:
                            data = json.loads(line)
                            if isinstance(data, dict):
                                headers = list(data.keys())
        except Exception as e:
            logger.warning(f"Could not inspect file headers for schema detection: {e}")

        return SchemaRegistry.detect_schema(headers)

    @classmethod
    def run_pipeline(
        cls,
        file_path: str,
        filename: Optional[str] = None,
        batch_size: int = BATCH_SIZE,
        schema_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes full ingestion and recovery pipeline on a given file.
        """
        start_time = time.time()
        filename = filename or os.path.basename(file_path)
        file_ext = os.path.splitext(filename)[1].lower()

        logger.info(f"Ingestion started for file: {filename}", extra={'run_id': 'INITIALIZING'})

        # Validate file extension
        if file_ext not in ('.csv', '.json'):
            raise ValueError(f"Unsupported file format '{file_ext}'. Supported formats: .csv, .json")

        # Validate file existence & size
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found at: {file_path}")

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            # Handle empty file
            run = PipelineRun.objects.create(
                run_id=uuid.uuid4(),
                filename=filename,
                run_status='FAILED',
                failure_reason='Input file is empty (0 bytes).',
                execution_duration=0.0,
                end_time=timezone.now(),
            )
            return {
                'run_id': str(run.run_id),
                'status': 'FAILED',
                'total_records': 0,
                'valid_records': 0,
                'rejected_records': 0,
                'published_records': 0,
                'failure_reason': 'Input file is empty (0 bytes).'
            }

        file_hash = cls.calculate_file_hash(file_path)

        # Register or retrieve SourceFile
        source_file_obj = SourceFile.objects.filter(file_hash=file_hash).first()
        if not source_file_obj:
            source_file_obj = SourceFile.objects.create(
                file_hash=file_hash,
                filename=filename,
                file_path=file_path,
                file_format=file_ext[1:].upper(),
                file_size_bytes=file_size,
                status='PROCESSING',
            )

        # Detect schema from file headers or explicit schema_name
        active_schema = cls._detect_file_schema(file_path, file_ext, schema_name=schema_name)

        # Create PipelineRun
        run_id = uuid.uuid4()
        pipeline_run = PipelineRun.objects.create(
            run_id=run_id,
            source_file=source_file_obj,
            filename=filename,
            run_status='RUNNING',
            metadata={
                'file_size_bytes': file_size,
                'file_hash': file_hash,
                'schema_detected': active_schema.name,
                'id_column': active_schema.id_column,
            }
        )

        logger.info(
            f"Pipeline run registered: {run_id} (schema: {active_schema.name})",
            extra={'run_id': str(run_id)}
        )

        total_records = 0
        valid_records_count = 0
        rejected_records_count = 0

        # Load valid customers set only if active schema requires customer FK validation
        valid_customer_ids = None
        if active_schema.name == 'ecommerce':
            valid_customer_ids = set(Customer.objects.values_list('customer_id', flat=True))

        duplicate_detector = DuplicateDetector(id_column=active_schema.id_column)

        try:
            records_generator = cls._read_records(file_path, file_ext, batch_size=batch_size)

            current_row = 0
            for chunk_records in records_generator:
                transformed_batch = []
                quarantine_items = []
                source_record_instances = []

                for raw_record in chunk_records:
                    current_row += 1
                    total_records += 1

                    # 1. Duplicate Check
                    is_dup, dup_errors = duplicate_detector.check_duplicate(
                        raw_record,
                        schema=active_schema,
                        source_file=filename,
                        source_row_number=current_row
                    )

                    if is_dup:
                        quarantine_items.append({
                            'record': raw_record,
                            'row_number': current_row,
                            'errors': dup_errors
                        })
                        source_record_instances.append(
                            SourceRecord(
                                run=pipeline_run,
                                source_file=filename,
                                source_row_number=current_row,
                                raw_data=raw_record,
                                is_valid=False
                            )
                        )
                        rejected_records_count += 1
                        continue

                    # 2. Schema Validation
                    is_schema_valid, schema_errors = SchemaValidator.validate_record(
                        raw_record,
                        schema=active_schema,
                        source_file=filename,
                        source_row_number=current_row
                    )

                    if not is_schema_valid:
                        quarantine_items.append({
                            'record': raw_record,
                            'row_number': current_row,
                            'errors': schema_errors
                        })
                        source_record_instances.append(
                            SourceRecord(
                                run=pipeline_run,
                                source_file=filename,
                                source_row_number=current_row,
                                raw_data=raw_record,
                                is_valid=False
                            )
                        )
                        rejected_records_count += 1
                        continue

                    # 3. Business Validation
                    is_biz_valid, biz_errors = BusinessValidator.validate_record(
                        raw_record,
                        schema=active_schema,
                        valid_customer_ids=valid_customer_ids,
                        source_file=filename,
                        source_row_number=current_row
                    )

                    if not is_biz_valid:
                        quarantine_items.append({
                            'record': raw_record,
                            'row_number': current_row,
                            'errors': biz_errors
                        })
                        source_record_instances.append(
                            SourceRecord(
                                run=pipeline_run,
                                source_file=filename,
                                source_row_number=current_row,
                                raw_data=raw_record,
                                is_valid=False
                            )
                        )
                        rejected_records_count += 1
                        continue

                    # Record is valid!
                    transformed = Transformer.transform_record(
                        raw_record,
                        schema=active_schema,
                        run_id=str(run_id),
                        source_file=filename,
                        source_row_number=current_row
                    )
                    transformed_batch.append(transformed)
                    source_record_instances.append(
                        SourceRecord(
                            run=pipeline_run,
                            source_file=filename,
                            source_row_number=current_row,
                            raw_data=raw_record,
                            is_valid=True
                        )
                    )
                    valid_records_count += 1

                # Flush batch to DB
                with transaction.atomic():
                    if source_record_instances:
                        SourceRecord.objects.bulk_create(source_record_instances, batch_size=2000)

                    if transformed_batch:
                        Publisher.publish_batch(transformed_batch)

                    if quarantine_items:
                        QuarantineManager.quarantine_batch(quarantine_items, run_id=str(run_id), source_file=filename)

            duration = round(time.time() - start_time, 3)

            # Determine run final status: COMPLETED_WITH_ERRORS if mixed valid/invalid
            if rejected_records_count == 0:
                final_status = 'COMPLETED'
            elif valid_records_count > 0:
                final_status = 'COMPLETED_WITH_ERRORS'
            else:
                final_status = 'FAILED'

            pipeline_run.total_records = total_records
            pipeline_run.valid_records = valid_records_count
            pipeline_run.rejected_records = rejected_records_count
            pipeline_run.processed_records = valid_records_count
            pipeline_run.execution_duration = duration
            pipeline_run.run_status = final_status
            pipeline_run.end_time = timezone.now()
            pipeline_run.save()

            source_file_obj.status = 'PROCESSED'
            source_file_obj.save()

            logger.info(
                f"Ingestion finished: {total_records} total, {valid_records_count} valid, "
                f"{rejected_records_count} quarantined in {duration}s",
                extra={'run_id': str(run_id)}
            )

            return {
                'run_id': str(run_id),
                'status': final_status,
                'total_records': total_records,
                'valid_records': valid_records_count,
                'rejected_records': rejected_records_count,
                'processed_records': valid_records_count,
                'execution_duration': duration,
                'source_file': filename,
            }

        except Exception as e:
            duration = round(time.time() - start_time, 3)
            pipeline_run.run_status = 'FAILED'
            pipeline_run.failure_reason = str(e)
            pipeline_run.execution_duration = duration
            pipeline_run.end_time = timezone.now()
            pipeline_run.save()

            source_file_obj.status = 'FAILED'
            source_file_obj.save()

            logger.error(f"Pipeline run {run_id} failed: {e}", exc_info=True, extra={'run_id': str(run_id)})
            raise

    @classmethod
    def _read_records(cls, file_path: str, file_ext: str, batch_size: int = BATCH_SIZE):
        """Yields chunks of records as lists of dicts."""
        if file_ext == '.csv':
            chunk_iterator = pd.read_csv(file_path, chunksize=batch_size, dtype=str, keep_default_na=False)
            for df_chunk in chunk_iterator:
                yield df_chunk.to_dict(orient='records')
        elif file_ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                first_char = f.read(1)
                f.seek(0)
                if first_char == '[':
                    data = json.load(f)
                    for i in range(0, len(data), batch_size):
                        yield data[i:i + batch_size]
                else:
                    batch = []
                    for line in f:
                        line = line.strip()
                        if line:
                            batch.append(json.loads(line))
                            if len(batch) >= batch_size:
                                yield batch
                                batch = []
                    if batch:
                        yield batch

import pytest
import uuid
from decimal import Decimal
from django.utils import timezone

from apps.processing.models import ProcessedOrder
from apps.quarantine.models import QuarantineRecord, CorrectionHistory
from apps.replay.models import ReplayHistory
from data_pipeline.engine.schema_registry import SchemaRegistry
from data_pipeline.engine.schema_validator import SchemaValidator
from data_pipeline.engine.business_validator import BusinessValidator
from data_pipeline.engine.duplicate_detector import DuplicateDetector
from data_pipeline.engine.transformer import Transformer
from data_pipeline.engine.publisher import Publisher
from data_pipeline.engine.quarantine_manager import QuarantineManager
from data_pipeline.engine.replay_engine import ReplayEngine
from data_pipeline.engine.ingestion import IngestionEngine


class TestTelemetrySchemaValidation:
    """Tests schema validation rules for Asset Telemetry dataset."""

    @pytest.fixture(autouse=True)
    def setup_schema(self):
        self.schema = SchemaRegistry.get('telemetry')

    def test_schema_auto_detection(self):
        headers = ['reading_id', 'asset_code', 'metric_name', 'metric_value', 'unit', 'observed_at', 'quality_flag']
        detected = SchemaRegistry.detect_schema(headers)
        assert detected.name == 'telemetry'

    def test_valid_telemetry_record_schema(self):
        record = {
            'reading_id': 'READ-001',
            'asset_code': 'ASSET-101',
            'metric_name': 'temperature',
            'metric_value': '24.50',
            'unit': 'C',
            'observed_at': '2026-10-31T10:00:00Z',
            'quality_flag': 'GOOD',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is True
        assert len(errors) == 0

    def test_missing_required_telemetry_field(self):
        record = {
            # missing reading_id
            'asset_code': 'ASSET-101',
            'metric_name': 'temperature',
            'metric_value': '24.50',
            'unit': 'C',
            'observed_at': '2026-10-31T10:00:00Z',
            'quality_flag': 'GOOD',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_MISSING_FIELD' and e['field_name'] == 'reading_id' for e in errors)

    def test_empty_or_null_asset_code(self):
        record = {
            'reading_id': 'READ-002',
            'asset_code': '   ',
            'metric_name': 'pressure',
            'metric_value': '101.3',
            'unit': 'kPa',
            'observed_at': '2026-10-31T10:00:00Z',
            'quality_flag': 'GOOD',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_NULL_VALUE' and e['field_name'] == 'asset_code' for e in errors)

    def test_invalid_metric_value_type(self):
        record = {
            'reading_id': 'READ-003',
            'asset_code': 'ASSET-101',
            'metric_name': 'temperature',
            'metric_value': 'bad-number',
            'unit': 'C',
            'observed_at': '2026-10-31T10:00:00Z',
            'quality_flag': 'GOOD',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_TYPE' and e['field_name'] == 'metric_value' for e in errors)

    def test_invalid_observed_at_format(self):
        record = {
            'reading_id': 'READ-004',
            'asset_code': 'ASSET-101',
            'metric_name': 'temperature',
            'metric_value': '24.50',
            'unit': 'C',
            'observed_at': 'bad-timestamp',
            'quality_flag': 'GOOD',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_DATE_FORMAT' and e['field_name'] == 'observed_at' for e in errors)


class TestTelemetryBusinessValidation:
    """Tests business validation rules for Asset Telemetry dataset."""

    @pytest.fixture(autouse=True)
    def setup_schema(self):
        self.schema = SchemaRegistry.get('telemetry')

    def test_valid_metrics_and_units(self):
        valid_cases = [
            ('temperature', '25.0', 'C'),
            ('humidity', '65.5', '%'),
            ('pressure', '101.325', 'kPa'),
            ('vibration', '0.045', 'mm/s'),
        ]
        for metric, val, unit in valid_cases:
            record = {
                'reading_id': 'READ-OK',
                'asset_code': 'ASSET-01',
                'metric_name': metric,
                'metric_value': val,
                'unit': unit,
                'observed_at': '2026-10-31T12:00:00Z',
                'quality_flag': 'GOOD',
            }
            is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
            assert is_valid is True, f"Failed for {metric}: {errors}"

    def test_unknown_metric_name_rejected(self):
        record = {
            'reading_id': 'READ-10',
            'asset_code': 'ASSET-01',
            'metric_name': 'unknown_metric',
            'metric_value': '10.0',
            'unit': 'x',
            'observed_at': '2026-10-31T12:00:00Z',
            'quality_flag': 'GOOD',
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_METRIC_NAME' for e in errors)

    def test_invalid_unit_for_metric(self):
        # Pressure with 'psi' instead of 'kPa'
        record = {
            'reading_id': 'READ-11',
            'asset_code': 'ASSET-01',
            'metric_name': 'pressure',
            'metric_value': '75.0',
            'unit': 'psi',
            'observed_at': '2026-10-31T12:00:00Z',
            'quality_flag': 'GOOD',
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_UNIT' for e in errors)

    def test_humidity_boundary_exceeded(self):
        record = {
            'reading_id': 'READ-12',
            'asset_code': 'ASSET-01',
            'metric_name': 'humidity',
            'metric_value': '108.5',  # > 100.0
            'unit': '%',
            'observed_at': '2026-10-31T12:00:00Z',
            'quality_flag': 'GOOD',
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_BOUNDARY' for e in errors)

    def test_vibration_negative_boundary_rejected(self):
        record = {
            'reading_id': 'READ-13',
            'asset_code': 'ASSET-01',
            'metric_name': 'vibration',
            'metric_value': '-3.5',  # < 0.0
            'unit': 'mm/s',
            'observed_at': '2026-10-31T12:00:00Z',
            'quality_flag': 'GOOD',
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_BOUNDARY' for e in errors)

    def test_invalid_quality_flag_rejected(self):
        record = {
            'reading_id': 'READ-14',
            'asset_code': 'ASSET-01',
            'metric_name': 'temperature',
            'metric_value': '25.0',
            'unit': 'C',
            'observed_at': '2026-10-31T12:00:00Z',
            'quality_flag': 'UNKNOWN',
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_STATUS' for e in errors)


class TestTelemetryDuplicateDetection:
    """Tests duplicate reading_id detection and asset_code re-use."""

    def test_duplicate_reading_id_in_batch_rejected(self):
        schema = SchemaRegistry.get('telemetry')
        detector = DuplicateDetector(id_column='reading_id')
        rec1 = {'reading_id': 'READ-DUP-1', 'asset_code': 'ASSET-01'}
        rec2 = {'reading_id': 'READ-DUP-1', 'asset_code': 'ASSET-02'}

        is_dup1, _ = detector.check_duplicate(rec1, schema=schema)
        assert is_dup1 is False

        is_dup2, errors2 = detector.check_duplicate(rec2, schema=schema)
        assert is_dup2 is True
        assert any(e['error_code'] == 'ERR_DUPLICATE_RECORD_ID' for e in errors2)

    def test_repeated_asset_code_allowed(self):
        """Repeated asset_code values MUST NOT be treated as duplicates."""
        schema = SchemaRegistry.get('telemetry')
        detector = DuplicateDetector(id_column='reading_id')
        rec1 = {'reading_id': 'READ-A-1', 'asset_code': 'ASSET-SHARED'}
        rec2 = {'reading_id': 'READ-A-2', 'asset_code': 'ASSET-SHARED'}
        rec3 = {'reading_id': 'READ-A-3', 'asset_code': 'ASSET-SHARED'}

        assert detector.check_duplicate(rec1, schema=schema)[0] is False
        assert detector.check_duplicate(rec2, schema=schema)[0] is False
        assert detector.check_duplicate(rec3, schema=schema)[0] is False


@pytest.mark.django_db
class TestTelemetryPipelineExecution:
    """Tests end-to-end ingestion and replay with Asset Telemetry dataset."""

    def test_ingest_telemetry_sample_file(self):
        sample_path = r"sample_data/asset_telemetry_1000_records.csv"
        result = IngestionEngine.run_pipeline(sample_path)

        # 1000 total rows: exactly 900 valid, exactly 100 quarantined
        assert result['total_records'] == 1000
        assert result['valid_records'] == 900
        assert result['rejected_records'] == 100
        assert result['status'] == 'COMPLETED_WITH_ERRORS'

        # Check published records in ProcessedOrder target table
        assert ProcessedOrder.objects.filter(reading_id__isnull=False).count() == 900

        # Verify published fields on sample record
        sample_rec = ProcessedOrder.objects.filter(reading_id__isnull=False).first()
        assert sample_rec.reading_id is not None
        assert sample_rec.asset_code is not None
        assert sample_rec.metric_name in {'temperature', 'humidity', 'pressure', 'vibration'}
        assert sample_rec.unit in {'C', '%', 'kPa', 'mm/s'}
        assert sample_rec.quality_flag in {'GOOD', 'REVIEW'}

        # Verify quarantine records
        quarantine_records = QuarantineRecord.objects.filter(source_file='asset_telemetry_1000_records.csv')
        assert quarantine_records.count() == 100

        # Check error distribution in quarantine
        error_codes = set(quarantine_records.values_list('error_code', flat=True))
        assert 'ERR_NULL_VALUE' in error_codes
        assert 'ERR_DUPLICATE_RECORD_ID' in error_codes
        assert 'ERR_INVALID_METRIC_NAME' in error_codes
        assert 'ERR_INVALID_UNIT' in error_codes
        assert 'ERR_INVALID_BOUNDARY' in error_codes
        assert 'ERR_INVALID_STATUS' in error_codes
        assert 'ERR_INVALID_TYPE' in error_codes
        assert 'ERR_INVALID_DATE_FORMAT' in error_codes

    def test_reupload_idempotency_telemetry_sample(self):
        sample_path = r"sample_data/asset_telemetry_1000_records.csv"
        # First upload
        IngestionEngine.run_pipeline(sample_path)
        count_first = ProcessedOrder.objects.filter(reading_id__isnull=False).count()
        assert count_first == 900

        # Second upload (same file re-uploaded)
        IngestionEngine.run_pipeline(sample_path)
        count_second = ProcessedOrder.objects.filter(reading_id__isnull=False).count()
        # Strictly idempotent: count must not increase
        assert count_second == 900

    def test_telemetry_correction_and_replay(self):
        # Create an invalid quarantined telemetry record
        run_id = uuid.uuid4()
        q_rec = QuarantineRecord.objects.create(
            record_id='READ-REPLAY-01',
            source_file='telemetry_test.csv',
            source_row_number=12,
            run_id=run_id,
            raw_record={
                'reading_id': 'READ-REPLAY-01',
                'asset_code': 'ASSET-200',
                'metric_name': 'pressure',
                'metric_value': '85.0',
                'unit': 'psi',  # invalid unit for pressure
                'observed_at': '2026-10-31T16:00:00Z',
                'quality_flag': 'GOOD',
            },
            error_code='ERR_INVALID_UNIT',
            error_reason="Invalid unit 'psi' for metric 'pressure'. Expected 'kPa'.",
            validation_stage='BUSINESS',
            status='PENDING',
        )

        # Operator applies correction (changes unit to kPa)
        corrected_data = {
            'reading_id': 'READ-REPLAY-01',
            'asset_code': 'ASSET-200',
            'metric_name': 'pressure',
            'metric_value': '85.0',
            'unit': 'kPa',
            'observed_at': '2026-10-31T16:00:00Z',
            'quality_flag': 'GOOD',
        }
        updated = QuarantineManager.apply_correction(
            quarantine_id=str(q_rec.quarantine_id),
            corrected_payload=corrected_data,
            operator_name='test_operator',
            notes='Corrected unit from psi to kPa'
        )
        assert updated.status == 'CORRECTED'
        assert CorrectionHistory.objects.filter(quarantine_record=updated).count() == 1

        # Execute replay
        replay_res = ReplayEngine.execute_replay(quarantine_ids=[str(q_rec.quarantine_id)])
        assert replay_res['successful_count'] == 1
        assert replay_res['failed_count'] == 0

        # Verify record is marked REPLAYED in quarantine
        updated.refresh_from_db()
        assert updated.status == 'REPLAYED'

        # Verify published to ProcessedOrder
        published = ProcessedOrder.objects.get(order_id='READ-REPLAY-01')
        assert published.reading_id == 'READ-REPLAY-01'
        assert published.asset_code == 'ASSET-200'
        assert published.metric_name == 'pressure'
        assert published.unit == 'kPa'
        assert published.metric_value == Decimal('85.0000')


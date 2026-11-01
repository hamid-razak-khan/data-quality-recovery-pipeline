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


class TestGenericSchemaValidation:
    """Tests schema validation rules for generic dataset."""

    @pytest.fixture(autouse=True)
    def setup_schema(self):
        self.schema = SchemaRegistry.get('generic')

    def test_valid_generic_record_schema(self):
        record = {
            'record_id': 'REC-9001',
            'entity_id': 'ENT-101',
            'event_type': 'CREATED',
            'amount': '125.50',
            'quantity': '2',
            'event_timestamp': '2026-10-31T10:00:00Z',
            'status': 'ACTIVE',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is True
        assert len(errors) == 0

    def test_missing_required_generic_field(self):
        record = {
            # missing record_id
            'entity_id': 'ENT-101',
            'event_type': 'CREATED',
            'amount': '125.50',
            'quantity': '2',
            'event_timestamp': '2026-10-31T10:00:00Z',
            'status': 'ACTIVE',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_MISSING_FIELD' and e['field_name'] == 'record_id' for e in errors)

    def test_empty_or_null_entity_id(self):
        record = {
            'record_id': 'REC-9002',
            'entity_id': '   ',
            'event_type': 'CREATED',
            'amount': '125.50',
            'quantity': '2',
            'event_timestamp': '2026-10-31T10:00:00Z',
            'status': 'ACTIVE',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_NULL_VALUE' and e['field_name'] == 'entity_id' for e in errors)

    def test_invalid_amount_type(self):
        record = {
            'record_id': 'REC-9003',
            'entity_id': 'ENT-101',
            'event_type': 'CREATED',
            'amount': 'not-a-number',
            'quantity': '2',
            'event_timestamp': '2026-10-31T10:00:00Z',
            'status': 'ACTIVE',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_TYPE' and e['field_name'] == 'amount' for e in errors)

    def test_invalid_quantity_type(self):
        record = {
            'record_id': 'REC-9004',
            'entity_id': 'ENT-101',
            'event_type': 'CREATED',
            'amount': '10.00',
            'quantity': 'two',
            'event_timestamp': '2026-10-31T10:00:00Z',
            'status': 'ACTIVE',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_TYPE' and e['field_name'] == 'quantity' for e in errors)

    def test_invalid_timestamp_format(self):
        # A date without time is invalid for event_timestamp
        record = {
            'record_id': 'REC-9005',
            'entity_id': 'ENT-101',
            'event_type': 'CREATED',
            'amount': '10.00',
            'quantity': '1',
            'event_timestamp': '31/10/2026',
            'status': 'ACTIVE',
        }
        is_valid, errors = SchemaValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_DATE_FORMAT' and e['field_name'] == 'event_timestamp' for e in errors)


class TestGenericBusinessValidation:
    """Tests business validation rules for generic dataset."""

    @pytest.fixture(autouse=True)
    def setup_schema(self):
        self.schema = SchemaRegistry.get('generic')

    def test_valid_generic_business_rules(self):
        record = {
            'record_id': 'REC-9010',
            'entity_id': 'ENT-200',
            'event_type': 'UPDATED',
            'amount': '0.00',
            'quantity': 1,
            'event_timestamp': '2026-10-31T12:00:00Z',
            'status': 'COMPLETED',
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is True
        assert len(errors) == 0

    def test_negative_amount_rejected(self):
        record = {
            'record_id': 'REC-9011',
            'entity_id': 'ENT-200',
            'event_type': 'CREATED',
            'amount': '-15.50',
            'quantity': 1,
            'event_timestamp': '2026-10-31T12:00:00Z',
            'status': 'ACTIVE',
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_PRICE' and e['field_name'] == 'amount' for e in errors)

    def test_non_positive_quantity_rejected(self):
        record = {
            'record_id': 'REC-9012',
            'entity_id': 'ENT-200',
            'event_type': 'CREATED',
            'amount': '25.00',
            'quantity': 0,
            'event_timestamp': '2026-10-31T12:00:00Z',
            'status': 'ACTIVE',
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_QUANTITY' and e['field_name'] == 'quantity' for e in errors)

    def test_invalid_event_type_rejected(self):
        record = {
            'record_id': 'REC-9013',
            'entity_id': 'ENT-200',
            'event_type': 'PURCHASED',  # not in CREATED, UPDATED, COMPLETED, CANCELLED
            'amount': '25.00',
            'quantity': 1,
            'event_timestamp': '2026-10-31T12:00:00Z',
            'status': 'ACTIVE',
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_STATUS' and e['field_name'] == 'event_type' for e in errors)

    def test_invalid_status_rejected(self):
        record = {
            'record_id': 'REC-9014',
            'entity_id': 'ENT-200',
            'event_type': 'CREATED',
            'amount': '25.00',
            'quantity': 1,
            'event_timestamp': '2026-10-31T12:00:00Z',
            'status': 'PENDING',  # allowed for ecommerce, but NOT generic (ACTIVE, COMPLETED, CANCELLED)
        }
        is_valid, errors = BusinessValidator.validate_record(record, schema=self.schema)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_STATUS' and e['field_name'] == 'status' for e in errors)


class TestGenericDuplicateDetection:
    """Tests duplicate record_id detection within a batch."""

    def test_in_batch_duplicate_record_id(self):
        detector = DuplicateDetector(id_column='record_id')
        rec1 = {'record_id': 'REC-DUP-01', 'entity_id': 'ENT-1', 'amount': '10.00'}
        rec2 = {'record_id': 'REC-DUP-01', 'entity_id': 'ENT-2', 'amount': '20.00'}

        is_dup1, errors1 = detector.check_duplicate(rec1)
        assert is_dup1 is False
        assert len(errors1) == 0

        is_dup2, errors2 = detector.check_duplicate(rec2)
        assert is_dup2 is True
        assert any(e['error_code'] == 'ERR_DUPLICATE_RECORD_ID' for e in errors2)


@pytest.mark.django_db
class TestGenericPipelineExecution:
    """Tests end-to-end ingestion and replay with generic CSV dataset."""

    def test_ingest_generic_sample_2_csv(self):
        sample_path = r"sample_data/generic_pipeline_sample_2.csv"
        result = IngestionEngine.run_pipeline(sample_path)

        # 51 total rows: 41 valid, 10 quarantined
        assert result['total_records'] == 51
        assert result['valid_records'] == 41
        assert result['rejected_records'] == 10
        assert result['status'] == 'COMPLETED_WITH_ERRORS'

        # Check published records in ProcessedOrder target table
        assert ProcessedOrder.objects.filter(order_id__startswith='REC-').count() == 41

        # Check sample published record
        rec = ProcessedOrder.objects.get(order_id='REC-2001')
        assert rec.entity_id == 'ENT-701'
        assert rec.event_type == 'CREATED'
        assert rec.amount == Decimal('3200.74')
        assert rec.status == 'ACTIVE'

        # Check quarantine records and actual record IDs
        quarantine_records = QuarantineRecord.objects.filter(source_file='generic_pipeline_sample_2.csv')
        assert quarantine_records.count() == 10

        # Verify no fake GEN- IDs when record_id is present
        rec_ids = set(quarantine_records.values_list('record_id', flat=True))
        assert 'REC-2041' in rec_ids  # invalid amount 'abc'
        assert 'REC-2042' in rec_ids  # invalid quantity 'two'
        assert 'REC-2043' in rec_ids  # invalid status 'UNKNOWN'
        assert 'REC-2044' in rec_ids  # invalid event_type 'DELETED'
        assert 'REC-2045' in rec_ids  # missing entity_id
        assert 'REC-2046' in rec_ids  # negative amount -25.00
        assert 'REC-2047' in rec_ids  # negative quantity -3
        assert 'REC-2048' in rec_ids  # invalid date '31/10/2026'
        assert 'REC-2049' in rec_ids  # empty status
        assert 'REC-2001' in rec_ids  # duplicate record_id

    def test_reupload_idempotency_generic_sample(self):
        sample_path = r"sample_data/generic_pipeline_sample_2.csv"
        # First upload
        IngestionEngine.run_pipeline(sample_path)
        count_first = ProcessedOrder.objects.filter(order_id__startswith='REC-').count()
        assert count_first == 41

        # Second upload (same file re-uploaded)
        IngestionEngine.run_pipeline(sample_path)
        count_second = ProcessedOrder.objects.filter(order_id__startswith='REC-').count()
        # Strictly idempotent: count must not increase
        assert count_second == 41

    def test_generic_correction_and_replay(self):
        # Create an invalid quarantined record
        run_id = uuid.uuid4()
        q_rec = QuarantineRecord.objects.create(
            record_id='REC-REPLAY-99',
            source_file='generic_test.csv',
            source_row_number=5,
            run_id=run_id,
            raw_record={
                'record_id': 'REC-REPLAY-99',
                'entity_id': 'ENT-999',
                'event_type': 'CREATED',
                'amount': 'invalid_amount',
                'quantity': '1',
                'event_timestamp': '2026-10-31T15:00:00Z',
                'status': 'ACTIVE',
            },
            error_code='ERR_INVALID_TYPE',
            error_reason="Amount 'invalid_amount' is not a valid numeric value.",
            validation_stage='SCHEMA',
            status='PENDING',
        )

        # Operator applies correction
        corrected_data = {
            'record_id': 'REC-REPLAY-99',
            'entity_id': 'ENT-999',
            'event_type': 'CREATED',
            'amount': '550.00',
            'quantity': 2,
            'event_timestamp': '2026-10-31T15:00:00Z',
            'status': 'ACTIVE',
        }
        updated = QuarantineManager.apply_correction(
            quarantine_id=str(q_rec.quarantine_id),
            corrected_payload=corrected_data,
            operator_name='test_operator',
            notes='Corrected numeric amount formatting'
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
        published = ProcessedOrder.objects.get(order_id='REC-REPLAY-99')
        assert published.amount == Decimal('550.00')
        assert published.quantity == 2
        assert published.entity_id == 'ENT-999'
        assert published.event_type == 'CREATED'


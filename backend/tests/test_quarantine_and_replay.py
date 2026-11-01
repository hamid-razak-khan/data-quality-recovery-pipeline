import pytest
import uuid
from decimal import Decimal
from django.utils import timezone
from apps.processing.models import Customer, ProcessedOrder
from apps.quarantine.models import QuarantineRecord, CorrectionHistory
from apps.replay.models import ReplayHistory
from data_pipeline.engine.quarantine_manager import QuarantineManager
from data_pipeline.engine.replay_engine import ReplayEngine
from data_pipeline.engine.publisher import Publisher
from data_pipeline.generators.generate_data import SyntheticDataGenerator


@pytest.mark.django_db
class TestQuarantineAndControlledReplay:
    """
    Tests for Quarantine Management and Controlled Replay Engine:
    - Scenarios 18, 19, 20, 21, 22
    - The Primary End-to-End Replay Guarantee Scenario (1000 -> 900/100 -> 60 corrected -> 960/40)
    """

    def setup_method(self):
        # Create a test customer
        self.customer = Customer.objects.create(
            customer_id='CUST-TEST-001',
            customer_name='Alice Replay',
            email='alice@example.com',
            registration_date='2024-01-01',
            status='ACTIVE'
        )

    def test_replay_uncorrected_record_is_blocked(self):
        """Scenario 19: Uncorrected record (status PENDING) must NEVER be replayed."""
        q_rec = QuarantineRecord.objects.create(
            record_id='ORD-UNCORRECTED-01',
            source_file='test.csv',
            source_row_number=1,
            run_id=uuid.uuid4(),
            raw_record={
                'order_id': 'ORD-UNCORRECTED-01',
                'customer_id': 'CUST-TEST-001',
                'product_name': 'Test Item',
                'quantity': 0,  # Invalid
                'unit_price': '10.00',
                'total_amount': '0.00',
                'order_date': '2024-01-01T00:00:00Z',
                'order_status': 'PENDING'
            },
            error_code='ERR_INVALID_QUANTITY',
            error_reason='Quantity must be positive',
            validation_stage='BUSINESS',
            status='PENDING',  # NOT CORRECTED
            attempt_count=0
        )

        res = ReplayEngine.execute_replay(quarantine_ids=[str(q_rec.quarantine_id)])
        assert res['successful_count'] == 0
        assert res['total_submitted'] == 0

        # Verify not inserted into processed orders
        assert not ProcessedOrder.objects.filter(order_id='ORD-UNCORRECTED-01').exists()

        # Record remains pending
        q_rec.refresh_from_db()
        assert q_rec.status == 'PENDING'

    def test_corrected_record_replay_success(self):
        """Scenario 18: An operator corrects an invalid record and replays it successfully."""
        q_rec = QuarantineRecord.objects.create(
            record_id='ORD-CORRECT-01',
            source_file='test.csv',
            source_row_number=2,
            run_id=uuid.uuid4(),
            raw_record={
                'order_id': 'ORD-CORRECT-01',
                'customer_id': 'NONEXISTENT',
                'product_name': 'Desk Lamp',
                'quantity': 2,
                'unit_price': '25.00',
                'total_amount': '50.00',
                'order_date': '2024-01-01T00:00:00Z',
                'order_status': 'CONFIRMED'
            },
            error_code='ERR_INVALID_FK',
            error_reason='Invalid customer reference',
            validation_stage='BUSINESS',
            status='PENDING'
        )

        # Operator corrects the customer_id to a valid existing customer
        corrected_payload = dict(q_rec.raw_record)
        corrected_payload['customer_id'] = 'CUST-TEST-001'

        QuarantineManager.apply_correction(
            quarantine_id=str(q_rec.quarantine_id),
            corrected_payload=corrected_payload,
            operator_name='test_operator',
            notes='Corrected customer_id to CUST-TEST-001'
        )

        q_rec.refresh_from_db()
        assert q_rec.status == 'CORRECTED'
        assert q_rec.corrections.count() == 1

        # Trigger controlled replay
        res = ReplayEngine.execute_replay(quarantine_ids=[str(q_rec.quarantine_id)])
        assert res['successful_count'] == 1
        assert res['failed_count'] == 0

        # Verify target processed order published
        order = ProcessedOrder.objects.get(order_id='ORD-CORRECT-01')
        assert order.customer_id == 'CUST-TEST-001'
        assert order.quantity == 2
        assert order.total_amount == Decimal('50.00')

        # Verify quarantine status updated to REPLAYED
        q_rec.refresh_from_db()
        assert q_rec.status == 'REPLAYED'
        assert q_rec.replayed_at is not None

    def test_record_remains_invalid_after_faulty_correction(self):
        """Scenario 22: Operator corrects record, but new payload is still invalid."""
        q_rec = QuarantineRecord.objects.create(
            record_id='ORD-FAULTY-01',
            source_file='test.csv',
            source_row_number=3,
            run_id=uuid.uuid4(),
            raw_record={
                'order_id': 'ORD-FAULTY-01',
                'customer_id': 'CUST-TEST-001',
                'product_name': 'Speaker',
                'quantity': -5,
                'unit_price': '20.00',
                'total_amount': '-100.00',
                'order_date': '2024-01-01T00:00:00Z',
                'order_status': 'CONFIRMED'
            },
            error_code='ERR_INVALID_QUANTITY',
            error_reason='Negative quantity',
            validation_stage='BUSINESS',
            status='PENDING'
        )

        # Operator changes quantity to 0 (still invalid!)
        faulty_correction = dict(q_rec.raw_record)
        faulty_correction['quantity'] = 0

        QuarantineManager.apply_correction(
            quarantine_id=str(q_rec.quarantine_id),
            corrected_payload=faulty_correction
        )

        # Trigger replay
        res = ReplayEngine.execute_replay(quarantine_ids=[str(q_rec.quarantine_id)])
        assert res['successful_count'] == 0
        assert res['failed_count'] == 1

        # Record should transition to FAILED and remain in quarantine
        q_rec.refresh_from_db()
        assert q_rec.status == 'FAILED'
        assert q_rec.attempt_count == 1
        assert not ProcessedOrder.objects.filter(order_id='ORD-FAULTY-01').exists()

    def test_replaying_the_same_record_twice_is_idempotent(self):
        """Scenario 20: Replaying an already replayed record does not duplicate or reprocess."""
        q_rec = QuarantineRecord.objects.create(
            record_id='ORD-TWICE-01',
            source_file='test.csv',
            source_row_number=4,
            run_id=uuid.uuid4(),
            raw_record={
                'order_id': 'ORD-TWICE-01',
                'customer_id': 'CUST-TEST-001',
                'product_name': 'Webcam',
                'quantity': 1,
                'unit_price': '60.00',
                'total_amount': '60.00',
                'order_date': '2024-01-01T00:00:00Z',
                'order_status': 'CONFIRMED'
            },
            error_code='ERR_INVALID_FK',
            error_reason='Invalid FK',
            validation_stage='BUSINESS',
            status='CORRECTED',
            corrected_record={
                'order_id': 'ORD-TWICE-01',
                'customer_id': 'CUST-TEST-001',
                'product_name': 'Webcam',
                'quantity': 1,
                'unit_price': '60.00',
                'total_amount': '60.00',
                'order_date': '2024-01-01T00:00:00Z',
                'order_status': 'CONFIRMED'
            }
        )

        # 1st replay: should succeed
        res1 = ReplayEngine.execute_replay(quarantine_ids=[str(q_rec.quarantine_id)])
        assert res1['successful_count'] == 1
        assert ProcessedOrder.objects.filter(order_id='ORD-TWICE-01').count() == 1

        q_rec.refresh_from_db()
        assert q_rec.status == 'REPLAYED'

        # 2nd replay: status is now REPLAYED, so should NOT be selected
        res2 = ReplayEngine.execute_replay(quarantine_ids=[str(q_rec.quarantine_id)])
        assert res2['successful_count'] == 0
        assert res2['total_submitted'] == 0
        assert ProcessedOrder.objects.filter(order_id='ORD-TWICE-01').count() == 1

    def test_primary_replay_business_guarantee_scenario(self):
        """
        =======================================================================
        PRIMARY BUSINESS REQUIREMENT VERIFICATION SCENARIO (Section 16):
        FIRST EXECUTION:
        - 1,000 source records
        - 900 valid records
        - 100 invalid records
        - 900 successfully published
        - 100 quarantined

        CORRECTION:
        - Correct 60 rejected records

        REPLAY:
        - 60 corrected records selected
        - 60 successfully published
        - 40 remain quarantined
        - Previously successful 900 records are not unnecessarily reprocessed

        FINAL RESULT:
        - 960 successful target records
        - 40 pending quarantined records

        SECOND REPLAY:
        - No additional records inserted
        - No duplicate records
        - Previously replayed records remain unchanged
        =======================================================================
        """
        run_id = uuid.uuid4()
        source_file = "batch_1000_orders.csv"

        # 1. Simulate First Execution:
        # 900 valid records published directly
        valid_orders = [
            ProcessedOrder(
                order_id=f"ORD-BATCH-{i:04d}",
                customer_id='CUST-TEST-001',
                product_name=f"Product {i}",
                quantity=1,
                unit_price=Decimal("20.00"),
                total_amount=Decimal("20.00"),
                order_date=timezone.now(),
                order_status='CONFIRMED',
                source_file=source_file,
                source_row_number=i,
                run_id=run_id
            )
            for i in range(1, 901)
        ]
        ProcessedOrder.objects.bulk_create(valid_orders)
        assert ProcessedOrder.objects.count() == 900

        # 100 invalid records quarantined
        quarantine_records = [
            QuarantineRecord(
                record_id=f"ORD-BATCH-{i:04d}",
                source_file=source_file,
                source_row_number=i,
                run_id=run_id,
                raw_record={
                    'order_id': f"ORD-BATCH-{i:04d}",
                    'customer_id': 'NONEXISTENT_CUST',  # Invalid FK
                    'product_name': f"Quarantine Item {i}",
                    'quantity': 1,
                    'unit_price': '25.00',
                    'total_amount': '25.00',
                    'order_date': '2024-03-01T12:00:00Z',
                    'order_status': 'CONFIRMED'
                },
                error_code='ERR_INVALID_FK',
                error_reason="Customer 'NONEXISTENT_CUST' does not exist.",
                validation_stage='BUSINESS',
                status='PENDING'
            )
            for i in range(901, 1001)
        ]
        QuarantineRecord.objects.bulk_create(quarantine_records)
        assert QuarantineRecord.objects.count() == 100

        # 2. Operator Correction:
        # Correct exactly 60 rejected records (from 901 to 960)
        quarantine_to_correct = list(QuarantineRecord.objects.filter(status='PENDING')[:60])
        assert len(quarantine_to_correct) == 60

        corrected_ids = []
        for q_rec in quarantine_to_correct:
            corrected_payload = dict(q_rec.raw_record)
            corrected_payload['customer_id'] = 'CUST-TEST-001'  # Fixed to valid customer
            QuarantineManager.apply_correction(
                quarantine_id=str(q_rec.quarantine_id),
                corrected_payload=corrected_payload,
                operator_name='operator_lead',
                notes='Batch fix customer FK'
            )
            corrected_ids.append(str(q_rec.quarantine_id))

        # Check statuses after correction
        assert QuarantineRecord.objects.filter(status='CORRECTED').count() == 60
        assert QuarantineRecord.objects.filter(status='PENDING').count() == 40

        # 3. Trigger Controlled Replay:
        # Replay the 60 corrected records
        replay_res = ReplayEngine.execute_replay(quarantine_ids=corrected_ids)
        assert replay_res['total_submitted'] == 60
        assert replay_res['successful_count'] == 60
        assert replay_res['failed_count'] == 0

        # 4. Verify Final State:
        # Total successful in target DB must be 960!
        total_published = ProcessedOrder.objects.count()
        assert total_published == 960

        # Quarantined count remaining pending must be 40!
        remaining_pending = QuarantineRecord.objects.filter(status='PENDING').count()
        assert remaining_pending == 40

        # Quarantined replayed must be 60!
        replayed_count = QuarantineRecord.objects.filter(status='REPLAYED').count()
        assert replayed_count == 60

        # 5. Second Replay Trigger (Idempotency Check):
        second_replay_res = ReplayEngine.execute_replay(quarantine_ids=corrected_ids)
        # Because they are now REPLAYED, 0 eligible records should be selected
        assert second_replay_res['total_submitted'] == 0
        assert second_replay_res['successful_count'] == 0

        # Target DB count remains strictly 960
        assert ProcessedOrder.objects.count() == 960
        assert QuarantineRecord.objects.filter(status='PENDING').count() == 40
        assert QuarantineRecord.objects.filter(status='REPLAYED').count() == 60

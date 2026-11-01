import pytest
import os
import tempfile
import uuid
from decimal import Decimal
from apps.processing.models import Customer, ProcessedOrder
from apps.quarantine.models import QuarantineRecord
from apps.ingestion.models import PipelineRun
from data_pipeline.engine.ingestion import IngestionEngine


@pytest.mark.django_db
class TestPipelineIngestionEdgeCases:
    def setup_method(self):
        self.customer = Customer.objects.create(
            customer_id='CUST-PIPE-001',
            customer_name='Pipeline Tester',
            email='pipe@example.com',
            registration_date='2024-01-01',
            status='ACTIVE'
        )

    def test_empty_input_file(self):
        """Scenario 2: Empty input file (0 bytes) must fail gracefully with descriptive error."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            temp_path = f.name

        try:
            res = IngestionEngine.run_pipeline(temp_path)
            assert res['status'] == 'FAILED'
            assert res['total_records'] == 0
            assert 'empty' in res['failure_reason'].lower()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_partial_failure_processing(self):
        """
        Critical rule: One invalid record must not stop the entire batch.
        Valid records must be processed and published even when others fail.
        """
        csv_data = (
            "order_id,customer_id,product_name,quantity,unit_price,total_amount,order_date,order_status\n"
            "ORD-VALID-01,CUST-PIPE-001,Laptop Stand,1,30.00,30.00,2024-01-01T00:00:00Z,CONFIRMED\n"
            "ORD-INVALID-02,NON_EXISTENT,Bad Record,0,-10.00,0.00,invalid-date,UNKNOWN\n"
            "ORD-VALID-03,CUST-PIPE-001,Keyboard,2,50.00,100.00,2024-01-01T00:00:00Z,DELIVERED\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            res = IngestionEngine.run_pipeline(temp_path)
            assert res['total_records'] == 3
            assert res['valid_records'] == 2
            assert res['rejected_records'] == 1

            # Check that valid orders are published
            assert ProcessedOrder.objects.filter(order_id='ORD-VALID-01').exists()
            assert ProcessedOrder.objects.filter(order_id='ORD-VALID-03').exists()

            # Check that invalid order is quarantined
            assert QuarantineRecord.objects.filter(record_id='ORD-INVALID-02').exists()
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_same_file_processed_twice_idempotency(self):
        """Scenario 17: Reprocessing the exact same input file does not duplicate successful target records."""
        csv_data = (
            "order_id,customer_id,product_name,quantity,unit_price,total_amount,order_date,order_status\n"
            "ORD-IDEMPOTENT-01,CUST-PIPE-001,Desk Mat,1,20.00,20.00,2024-01-01T00:00:00Z,CONFIRMED\n"
            "ORD-IDEMPOTENT-02,CUST-PIPE-001,Mouse Pad,2,15.00,30.00,2024-01-01T00:00:00Z,DELIVERED\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_data)
            temp_path = f.name

        try:
            # 1st run
            res1 = IngestionEngine.run_pipeline(temp_path)
            assert res1['valid_records'] == 2
            assert ProcessedOrder.objects.filter(order_id__in=['ORD-IDEMPOTENT-01', 'ORD-IDEMPOTENT-02']).count() == 2

            # 2nd run with the exact same file
            res2 = IngestionEngine.run_pipeline(temp_path)
            assert res2['valid_records'] == 2

            # Target count MUST STILL BE EXACTLY 2 (no duplicate rows created!)
            assert ProcessedOrder.objects.filter(order_id__in=['ORD-IDEMPOTENT-01', 'ORD-IDEMPOTENT-02']).count() == 2
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

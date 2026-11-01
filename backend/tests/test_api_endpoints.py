import pytest
import io
import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIClient
from apps.processing.models import Customer, ProcessedOrder
from apps.quarantine.models import QuarantineRecord
from apps.ingestion.models import PipelineRun, SourceFile


@pytest.mark.django_db
class TestApiEndpoints:
    def setup_method(self):
        self.client = APIClient()
        self.customer = Customer.objects.create(
            customer_id='CUST-API-001',
            customer_name='API Test Customer',
            email='api.test@example.com',
            registration_date='2024-01-01',
            status='ACTIVE'
        )

    def test_file_upload_csv(self):
        csv_content = (
            "order_id,customer_id,product_name,quantity,unit_price,total_amount,order_date,order_status\n"
            "ORD-API-01,CUST-API-001,Wireless Mouse,1,25.00,25.00,2024-01-01T00:00:00Z,CONFIRMED\n"
        )
        file_obj = io.BytesIO(csv_content.encode('utf-8'))
        file_obj.name = 'test_orders.csv'

        response = self.client.post('/api/ingestion/upload/', {'file': file_obj}, format='multipart')
        assert response.status_code == 201
        assert 'file' in response.data
        assert response.data['file']['filename'] == 'test_orders.csv'
        assert len(response.data['preview']) == 1

    def test_pipeline_runs_list(self):
        run = PipelineRun.objects.create(
            run_id=uuid.uuid4(),
            filename='test_run.csv',
            total_records=100,
            valid_records=90,
            rejected_records=10,
            run_status='COMPLETED_WITH_ERRORS'
        )
        response = self.client.get('/api/pipeline/runs/')
        assert response.status_code == 200
        assert response.data['count'] >= 1

    def test_quarantine_list_and_summary(self):
        q = QuarantineRecord.objects.create(
            record_id='ORD-QUAR-01',
            source_file='sample.csv',
            source_row_number=1,
            run_id=uuid.uuid4(),
            raw_record={'order_id': 'ORD-QUAR-01', 'quantity': 0},
            error_code='ERR_INVALID_QUANTITY',
            error_reason='Zero quantity',
            validation_stage='BUSINESS',
            status='PENDING'
        )

        # GET /api/quarantine/
        list_resp = self.client.get('/api/quarantine/')
        assert list_resp.status_code == 200
        assert list_resp.data['count'] >= 1

        # GET /api/quarantine/summary/
        summary_resp = self.client.get('/api/quarantine/summary/')
        assert summary_resp.status_code == 200
        assert 'total_quarantined' in summary_resp.data

        # GET /api/quarantine/{id}/
        detail_resp = self.client.get(f'/api/quarantine/{q.quarantine_id}/')
        assert detail_resp.status_code == 200
        assert detail_resp.data['record_id'] == 'ORD-QUAR-01'

    def test_quarantine_correction_patch(self):
        q = QuarantineRecord.objects.create(
            record_id='ORD-PATCH-01',
            source_file='sample.csv',
            source_row_number=5,
            run_id=uuid.uuid4(),
            raw_record={'order_id': 'ORD-PATCH-01', 'quantity': -1, 'unit_price': '10.00'},
            error_code='ERR_INVALID_QUANTITY',
            error_reason='Negative quantity',
            validation_stage='BUSINESS',
            status='PENDING'
        )

        corrected = {
            'order_id': 'ORD-PATCH-01',
            'customer_id': 'CUST-API-001',
            'product_name': 'Keycap Set',
            'quantity': 2,
            'unit_price': '15.00',
            'total_amount': '30.00',
            'order_date': '2024-01-01T00:00:00Z',
            'order_status': 'CONFIRMED'
        }

        patch_resp = self.client.patch(
            f'/api/quarantine/{q.quarantine_id}/correct/',
            {'corrected_record': corrected, 'notes': 'Fixed quantity and added full fields'},
            format='json'
        )
        assert patch_resp.status_code == 200
        assert patch_resp.data['record']['status'] == 'CORRECTED'

    def test_replay_trigger_api(self):
        q = QuarantineRecord.objects.create(
            record_id='ORD-REPLAY-API-01',
            source_file='sample.csv',
            source_row_number=10,
            run_id=uuid.uuid4(),
            raw_record={'order_id': 'ORD-REPLAY-API-01'},
            corrected_record={
                'order_id': 'ORD-REPLAY-API-01',
                'customer_id': 'CUST-API-001',
                'product_name': 'Monitor Arm',
                'quantity': 1,
                'unit_price': '50.00',
                'total_amount': '50.00',
                'order_date': '2024-01-01T00:00:00Z',
                'order_status': 'CONFIRMED'
            },
            error_code='ERR_INVALID_FK',
            error_reason='Invalid customer',
            validation_stage='BUSINESS',
            status='CORRECTED'
        )

        replay_resp = self.client.post(
            '/api/replay/',
            {'record_ids': [str(q.quarantine_id)]},
            format='json'
        )
        assert replay_resp.status_code == 200
        assert replay_resp.data['successful_count'] == 1
        assert ProcessedOrder.objects.filter(order_id='ORD-REPLAY-API-01').exists()

    def test_processed_orders_and_csv_export(self):
        ProcessedOrder.objects.create(
            order_id='ORD-EXPORT-01',
            customer=self.customer,
            product_name='Desk Mat',
            quantity=1,
            unit_price=Decimal('20.00'),
            total_amount=Decimal('20.00'),
            order_date=timezone.now(),
            order_status='CONFIRMED',
            source_file='test.csv',
            source_row_number=1,
            run_id=uuid.uuid4()
        )

        # JSON List
        resp = self.client.get('/api/processed/')
        assert resp.status_code == 200
        assert resp.data['count'] >= 1

        # CSV Export
        export_resp = self.client.get('/api/processed/?export=csv')
        assert export_resp.status_code == 200
        assert export_resp['Content-Type'] == 'text/csv'
        assert b'ORD-EXPORT-01' in export_resp.content

    def test_metrics_and_reconciliation(self):
        # Create sample runs and records
        run1 = PipelineRun.objects.create(
            run_id=uuid.uuid4(),
            filename='asset_telemetry_sample.csv',
            total_records=1000,
            valid_records=900,
            rejected_records=100,
            execution_duration=4.5,
            run_status='COMPLETED_WITH_ERRORS',
            metadata={'schema_detected': 'telemetry'},
        )
        run2 = PipelineRun.objects.create(
            run_id=uuid.uuid4(),
            filename='generic_records_sample.csv',
            total_records=500,
            valid_records=500,
            rejected_records=0,
            execution_duration=2.0,
            run_status='COMPLETED',
            metadata={'schema_detected': 'generic'},
        )

        QuarantineRecord.objects.create(
            record_id='READ-ERR-01',
            source_file='asset_telemetry_sample.csv',
            source_row_number=1,
            run_id=run1.run_id,
            raw_record={'reading_id': 'READ-ERR-01'},
            error_code='ERR_INVALID_UNIT',
            error_reason='Invalid unit',
            validation_stage='BUSINESS',
            status='PENDING'
        )
        QuarantineRecord.objects.create(
            record_id='READ-ERR-02',
            source_file='asset_telemetry_sample.csv',
            source_row_number=2,
            run_id=run1.run_id,
            raw_record={'reading_id': 'READ-ERR-02'},
            error_code='ERR_INVALID_UNIT',
            error_reason='Invalid unit',
            validation_stage='BUSINESS',
            status='REPLAYED'
        )

        metrics_resp = self.client.get('/api/metrics/')
        assert metrics_resp.status_code == 200
        assert 'kpis' in metrics_resp.data
        assert 'performance' in metrics_resp.data
        assert 'reconciliation_ledger' in metrics_resp.data
        assert 'quality_trends' in metrics_resp.data
        assert 'error_breakdown' in metrics_resp.data

        # Verify performance metrics
        perf = metrics_resp.data['performance']
        assert perf['avg_throughput_rps'] > 0
        assert perf['avg_duration_seconds'] > 0
        assert perf['total_batches_executed'] >= 2

        # Verify reconciliation ledger
        ledger = metrics_resp.data['reconciliation_ledger']
        assert ledger['ingestion_formula_balanced'] is True
        assert ledger['quarantine_formula_balanced'] is True
        assert ledger['total_source_records_ingested'] >= 1500

        # Verify error breakdown with active vs historical
        err_breakdown = metrics_resp.data['error_breakdown']
        unit_err = next((e for e in err_breakdown if e['error_code'] == 'ERR_INVALID_UNIT'), None)
        assert unit_err is not None
        assert unit_err['count'] == 2
        assert unit_err['active_count'] == 1
        assert unit_err['historical_count'] == 1

        # Test filtering trends by schema
        filter_telem_resp = self.client.get('/api/metrics/?schema=telemetry')
        assert filter_telem_resp.status_code == 200
        trends = filter_telem_resp.data['quality_trends']
        assert all(t['schema'] == 'telemetry' for t in trends)

        # Test filtering trends by status
        filter_status_resp = self.client.get('/api/metrics/?status=COMPLETED')
        assert filter_status_resp.status_code == 200
        status_trends = filter_status_resp.data['quality_trends']
        assert all(t['run_status'] == 'COMPLETED' for t in status_trends)

        recon_resp = self.client.get('/api/metrics/reconciliation/')
        assert recon_resp.status_code == 200
        assert 'global_reconciliation' in recon_resp.data
        assert recon_resp.data['global_reconciliation']['ingestion_formula_balanced'] is True

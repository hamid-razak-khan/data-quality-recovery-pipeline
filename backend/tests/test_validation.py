import pytest
from decimal import Decimal
from data_pipeline.engine.schema_validator import SchemaValidator
from data_pipeline.engine.business_validator import BusinessValidator
from data_pipeline.engine.duplicate_detector import DuplicateDetector
from data_pipeline.engine.transformer import Transformer


class TestSchemaValidation:
    """Tests 1, 5, 6, 7, 14: Happy path, missing fields, null values, invalid types, unexpected schemas."""

    def test_happy_path_schema(self):
        record = {
            'order_id': 'ORD-0001',
            'customer_id': 'CUST-001',
            'product_name': 'Mechanical Keyboard',
            'quantity': '2',
            'unit_price': '49.99',
            'total_amount': '99.98',
            'order_date': '2024-03-15T10:30:00Z',
            'order_status': 'CONFIRMED',
        }
        is_valid, errors = SchemaValidator.validate_record(record)
        assert is_valid is True
        assert len(errors) == 0

    def test_missing_required_fields(self):
        record = {
            'order_id': 'ORD-0002',
            # missing customer_id
            'product_name': 'Mouse',
            'quantity': '1',
            'unit_price': '20.00',
            'total_amount': '20.00',
            'order_date': '2024-03-15',
            'order_status': 'PENDING',
        }
        is_valid, errors = SchemaValidator.validate_record(record)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_MISSING_FIELD' and e['field_name'] == 'customer_id' for e in errors)

    def test_null_or_empty_values(self):
        record = {
            'order_id': '',
            'customer_id': None,
            'product_name': '   ',
            'quantity': '1',
            'unit_price': '10.00',
            'total_amount': '10.00',
            'order_date': '2024-01-01',
            'order_status': 'PENDING',
        }
        is_valid, errors = SchemaValidator.validate_record(record)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_NULL_VALUE' and e['field_name'] == 'order_id' for e in errors)
        assert any(e['error_code'] == 'ERR_NULL_VALUE' and e['field_name'] == 'customer_id' for e in errors)

    def test_incorrect_data_types(self):
        record = {
            'order_id': 'ORD-0003',
            'customer_id': 'CUST-001',
            'product_name': 'Desk',
            'quantity': 'two_pieces',  # not an integer
            'unit_price': 'free',       # not a decimal
            'total_amount': '99.99',
            'order_date': '2024-01-01',
            'order_status': 'PENDING',
        }
        is_valid, errors = SchemaValidator.validate_record(record)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_TYPE' and e['field_name'] == 'quantity' for e in errors)
        assert any(e['error_code'] == 'ERR_INVALID_TYPE' and e['field_name'] == 'unit_price' for e in errors)

    def test_malformed_order_date(self):
        record = {
            'order_id': 'ORD-0004',
            'customer_id': 'CUST-001',
            'product_name': 'Desk',
            'quantity': '1',
            'unit_price': '50.00',
            'total_amount': '50.00',
            'order_date': 'not-a-valid-date-string',
            'order_status': 'PENDING',
        }
        is_valid, errors = SchemaValidator.validate_record(record)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_DATE_FORMAT' for e in errors)


class TestBusinessValidation:
    """Tests 8, 9, 10, 11, 12, 13: FK, positive qty, positive price, calculation, status, duplicates."""

    def test_invalid_foreign_key(self):
        valid_customers = {'CUST-001', 'CUST-002'}
        record = {
            'order_id': 'ORD-0005',
            'customer_id': 'NONEXISTENT_CUST',
            'product_name': 'Monitor',
            'quantity': 1,
            'unit_price': '200.00',
            'total_amount': '200.00',
            'order_date': '2024-02-01',
            'order_status': 'CONFIRMED',
        }
        is_valid, errors = BusinessValidator.validate_record(record, valid_customer_ids=valid_customers)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_FK' for e in errors)

    def test_zero_or_negative_quantity(self):
        valid_customers = {'CUST-001'}
        record = {
            'order_id': 'ORD-0006',
            'customer_id': 'CUST-001',
            'product_name': 'Monitor',
            'quantity': 0,
            'unit_price': '100.00',
            'total_amount': '0.00',
            'order_date': '2024-02-01',
            'order_status': 'CONFIRMED',
        }
        is_valid, errors = BusinessValidator.validate_record(record, valid_customer_ids=valid_customers)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_QUANTITY' for e in errors)

    def test_negative_unit_price(self):
        valid_customers = {'CUST-001'}
        record = {
            'order_id': 'ORD-0007',
            'customer_id': 'CUST-001',
            'product_name': 'Monitor',
            'quantity': 2,
            'unit_price': '-50.00',
            'total_amount': '-100.00',
            'order_date': '2024-02-01',
            'order_status': 'CONFIRMED',
        }
        is_valid, errors = BusinessValidator.validate_record(record, valid_customer_ids=valid_customers)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_PRICE' for e in errors)

    def test_calculation_mismatch(self):
        valid_customers = {'CUST-001'}
        record = {
            'order_id': 'ORD-0008',
            'customer_id': 'CUST-001',
            'product_name': 'Cable',
            'quantity': 3,
            'unit_price': '10.00',
            'total_amount': '45.00',  # Should be 30.00!
            'order_date': '2024-02-01',
            'order_status': 'CONFIRMED',
        }
        is_valid, errors = BusinessValidator.validate_record(record, valid_customer_ids=valid_customers)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_CALCULATION_MISMATCH' for e in errors)

    def test_invalid_order_status(self):
        valid_customers = {'CUST-001'}
        record = {
            'order_id': 'ORD-0009',
            'customer_id': 'CUST-001',
            'product_name': 'Cable',
            'quantity': 1,
            'unit_price': '10.00',
            'total_amount': '10.00',
            'order_date': '2024-02-01',
            'order_status': 'DISPATCHED_TO_MARS',  # Invalid enum value
        }
        is_valid, errors = BusinessValidator.validate_record(record, valid_customer_ids=valid_customers)
        assert is_valid is False
        assert any(e['error_code'] == 'ERR_INVALID_STATUS' for e in errors)

    def test_duplicate_order_id_within_batch(self):
        detector = DuplicateDetector()
        record1 = {'order_id': 'ORD-DUPLICATE-01'}
        record2 = {'order_id': 'ORD-DUPLICATE-01'}

        is_dup1, errors1 = detector.check_duplicate(record1)
        assert is_dup1 is False
        assert len(errors1) == 0

        is_dup2, errors2 = detector.check_duplicate(record2)
        assert is_dup2 is True
        assert any(e['error_code'] == 'ERR_DUPLICATE_ORDER_ID' for e in errors2)


class TestTransformation:
    def test_transformation_normalization(self):
        raw = {
            'order_id': '  ORD-999  ',
            'customer_id': '  CUST-001  ',
            'product_name': '  Wireless   Ergonomic    Mouse  ',
            'quantity': '2',
            'unit_price': '29.99',
            'total_amount': '59.98',
            'order_date': '2024-04-10T15:30:00+00:00',
            'order_status': 'pending',
        }
        res = Transformer.transform_record(raw, run_id='test-run', source_file='test.csv', source_row_number=1)
        assert res['order_id'] == 'ORD-999'
        assert res['customer_id'] == 'CUST-001'
        assert res['product_name'] == 'Wireless Ergonomic Mouse'
        assert res['order_status'] == 'PENDING'
        assert res['quantity'] == 2
        assert res['unit_price'] == Decimal('29.99')
        assert res['total_amount'] == Decimal('59.98')
        assert res['order_date'].tzinfo is not None

from rest_framework import serializers
from apps.processing.models import Customer, ProcessedOrder


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            'customer_id',
            'customer_name',
            'email',
            'registration_date',
            'status',
            'created_at',
            'updated_at',
        ]


class ProcessedOrderSerializer(serializers.ModelSerializer):
    record_id = serializers.CharField(source='order_id', read_only=True)
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True, default='')
    customer_email = serializers.CharField(source='customer.email', read_only=True, default='')

    class Meta:
        model = ProcessedOrder
        fields = [
            'record_id',
            'order_id',
            'reading_id',
            'asset_code',
            'metric_name',
            'metric_value',
            'unit',
            'observed_at',
            'quality_flag',
            'entity_id',
            'event_type',
            'amount',
            'quantity',
            'event_timestamp',
            'status',
            'customer_id',
            'customer_name',
            'customer_email',
            'product_name',
            'unit_price',
            'total_amount',
            'order_date',
            'order_status',
            'source_file',
            'source_row_number',
            'run_id',
            'processed_at',
            'updated_at',
        ]

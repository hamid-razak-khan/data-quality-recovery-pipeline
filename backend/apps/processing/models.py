from django.db import models


class Customer(models.Model):
    customer_id = models.CharField(max_length=64, primary_key=True)
    customer_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    registration_date = models.DateField()
    status = models.CharField(max_length=32, default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customers'
        ordering = ['customer_id']

    def __str__(self):
        return f"{self.customer_id} - {self.customer_name}"


class ProcessedOrder(models.Model):
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
    ]

    order_id = models.CharField(max_length=128, primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders', null=True, blank=True)

    # Generic schema fields
    entity_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    event_type = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    quantity = models.IntegerField(null=True, blank=True)
    event_timestamp = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=32, null=True, blank=True, db_index=True)

    # Asset Telemetry schema fields
    reading_id = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    asset_code = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    metric_name = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    metric_value = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=32, null=True, blank=True)
    observed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    quality_flag = models.CharField(max_length=32, null=True, blank=True, db_index=True)

    # E-commerce schema fields
    product_name = models.CharField(max_length=255, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    order_date = models.DateTimeField(null=True, blank=True, db_index=True)
    order_status = models.CharField(max_length=32, choices=ORDER_STATUS_CHOICES, null=True, blank=True, db_index=True)

    source_file = models.CharField(max_length=255)
    source_row_number = models.IntegerField()
    run_id = models.UUIDField(db_index=True)
    raw_payload = models.JSONField(null=True, blank=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'processed_orders'
        ordering = ['-processed_at']
        indexes = [
            models.Index(fields=['customer', 'order_status']),
            models.Index(fields=['run_id', 'processed_at']),
            models.Index(fields=['entity_id', 'status']),
            models.Index(fields=['asset_code', 'metric_name']),
        ]

    @property
    def record_id(self):
        return self.order_id

    @record_id.setter
    def record_id(self, val):
        self.order_id = val

    def __str__(self):
        return f"Record {self.order_id} ({self.status or self.order_status}) - {self.amount or self.total_amount}"

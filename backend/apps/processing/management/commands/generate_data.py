"""
Management command to generate synthetic customer and order datasets.
Usage: python manage.py generate_data --records 100000 --seed 42
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.processing.models import Customer
from data_pipeline.generators.generate_data import SyntheticDataGenerator


class Command(BaseCommand):
    help = 'Generates synthetic datasets for orders and customers'

    def add_arguments(self, parser):
        parser.add_argument('--records', type=int, default=1000, help='Number of order records to generate')
        parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility')
        parser.add_argument('--customers', type=int, default=500, help='Number of customers to generate')
        parser.add_argument('--invalid-ratio', type=float, default=0.10, help='Fraction of records that are invalid')
        parser.add_argument('--out-dir', type=str, default=None, help='Output directory for generated files')

    def handle(self, *args, **options):
        records = options['records']
        seed = options['seed']
        customer_count = options['customers']
        invalid_ratio = options['invalid_ratio']

        base_dir = options['out_dir'] or os.path.join(settings.BASE_DIR, '..', 'sample_data')
        os.makedirs(base_dir, exist_ok=True)

        self.stdout.write(f"Initializing SyntheticDataGenerator with seed={seed}...")
        gen = SyntheticDataGenerator(seed=seed)

        # 1. Generate customers
        customers = gen.generate_customers(count=customer_count)
        cust_csv_path = os.path.join(base_dir, 'customers.csv')
        gen.write_csv(customers, cust_csv_path)
        self.stdout.write(self.style.SUCCESS(f"Generated {len(customers)} customers -> {cust_csv_path}"))

        # Seed customers to database if not present
        existing_cust_count = Customer.objects.count()
        if existing_cust_count < customer_count:
            cust_instances = [
                Customer(
                    customer_id=c['customer_id'],
                    customer_name=c['customer_name'],
                    email=c['email'],
                    registration_date=c['registration_date'],
                    status=c['status'],
                )
                for c in customers
            ]
            Customer.objects.bulk_create(cust_instances, ignore_conflicts=True, batch_size=1000)
            self.stdout.write(self.style.SUCCESS(f"Seeded {len(customers)} customers into PostgreSQL database."))

        # 2. Generate orders
        valid_cust_ids = [c['customer_id'] for c in customers]
        self.stdout.write(f"Generating {records} orders (approx. {int(invalid_ratio*100)}% invalid)...")
        orders = gen.generate_orders(
            record_count=records,
            customer_ids=valid_cust_ids,
            invalid_ratio=invalid_ratio
        )

        orders_csv_path = os.path.join(base_dir, f'orders_{records}.csv')
        gen.write_csv(orders, orders_csv_path)
        self.stdout.write(self.style.SUCCESS(f"Generated {len(orders)} orders -> {orders_csv_path}"))

        # Also write a standard orders.csv and orders.json in sample_data
        gen.write_csv(orders, os.path.join(base_dir, 'orders.csv'))
        gen.write_json(orders[:500], os.path.join(base_dir, 'orders_sample.json'))
        self.stdout.write(self.style.SUCCESS(f"Saved default sample_data/orders.csv and sample_data/orders_sample.json"))

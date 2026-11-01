"""
Management command to seed reference customers in Supabase PostgreSQL.
"""
from django.core.management.base import BaseCommand
from apps.processing.models import Customer
from data_pipeline.generators.generate_data import SyntheticDataGenerator


class Command(BaseCommand):
    help = 'Seeds initial customer master data into Supabase PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=500, help='Number of customers to seed')

    def handle(self, *args, **options):
        count = options['count']
        self.stdout.write(f"Generating and seeding {count} reference customers...")

        generator = SyntheticDataGenerator(seed=42)
        customers_data = generator.generate_customers(count=count)

        instances = [
            Customer(
                customer_id=c['customer_id'],
                customer_name=c['customer_name'],
                email=c['email'],
                registration_date=c['registration_date'],
                status=c['status'],
            )
            for c in customers_data
        ]

        created = Customer.objects.bulk_create(instances, ignore_conflicts=True, batch_size=1000)
        total = Customer.objects.count()
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded customers! Total customers in database: {total}"))

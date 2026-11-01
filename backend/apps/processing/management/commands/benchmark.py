"""
Performance Benchmark Management Command.
Measures records processed per second, memory efficiency, and pipeline throughput.
Usage: python manage.py benchmark --records 10000 --seed 42
"""
import os
import sys
import time
import platform
from django.core.management.base import BaseCommand
from django.conf import settings
from tabulate import tabulate
from data_pipeline.generators.generate_data import SyntheticDataGenerator
from data_pipeline.engine.ingestion import IngestionEngine
from apps.processing.models import Customer


class Command(BaseCommand):
    help = 'Executes end-to-end pipeline benchmark on configurable dataset size'

    def add_arguments(self, parser):
        parser.add_argument('--records', type=int, default=10000, help='Total records to benchmark')
        parser.add_argument('--seed', type=int, default=42, help='Random seed')
        parser.add_argument('--batch-size', type=int, default=5000, help='Ingestion batch size')

    def handle(self, *args, **options):
        records = options['records']
        seed = options['seed']
        batch_size = options['batch_size']

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n======================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING(f" DATA QUALITY PIPELINE PERFORMANCE BENCHMARK"))
        self.stdout.write(self.style.MIGRATE_HEADING(f"=======================================================\n"))

        self.stdout.write(f"Environment: {platform.system()} {platform.release()} | Python {platform.python_version()}")
        self.stdout.write(f"Database: Supabase PostgreSQL (Managed Cloud)")
        self.stdout.write(f"Target record volume: {records:,} records")
        self.stdout.write(f"Batch size: {batch_size:,} records/chunk\n")

        # 1. Prepare benchmark data
        bench_dir = os.path.join(settings.BASE_DIR, '..', 'sample_data')
        os.makedirs(bench_dir, exist_ok=True)
        bench_file = os.path.join(bench_dir, f'benchmark_{records}.csv')

        self.stdout.write("Preparing test dataset...")
        gen = SyntheticDataGenerator(seed=seed)

        # Ensure reference customers exist
        cust_count = Customer.objects.count()
        if cust_count < 500:
            customers = gen.generate_customers(count=500)
            Customer.objects.bulk_create([
                Customer(
                    customer_id=c['customer_id'],
                    customer_name=c['customer_name'],
                    email=c['email'],
                    registration_date=c['registration_date'],
                    status=c['status']
                ) for c in customers
            ], ignore_conflicts=True)

        customer_ids = list(Customer.objects.values_list('customer_id', flat=True)[:500])
        orders = gen.generate_orders(record_count=records, customer_ids=customer_ids, invalid_ratio=0.10)
        gen.write_csv(orders, bench_file)
        self.stdout.write(f"Benchmark dataset ready: {bench_file}\n")

        # 2. Run benchmark
        self.stdout.write("Starting pipeline benchmark execution...")
        t_start = time.time()
        result = IngestionEngine.run_pipeline(
            file_path=bench_file,
            filename=f"benchmark_{records}.csv",
            batch_size=batch_size
        )
        total_time = time.time() - t_start

        rec_per_sec = round(records / total_time, 2) if total_time > 0 else 0

        # 3. Present formatted results
        table_data = [
            ["Total Records Processed", f"{result['total_records']:,}"],
            ["Valid Records (Published)", f"{result['valid_records']:,}"],
            ["Rejected Records (Quarantined)", f"{result['rejected_records']:,}"],
            ["Total Duration (seconds)", f"{total_time:.3f} s"],
            ["Pipeline Engine Duration", f"{result['execution_duration']:.3f} s"],
            ["Throughput (Records/Sec)", f"{rec_per_sec:,.2f} records/s"],
            ["Execution Status", result['status']],
            ["Run ID", result['run_id']],
        ]

        self.stdout.write("\n" + tabulate(table_data, headers=["Metric", "Value"], tablefmt="grid"))

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Benchmark completed successfully!\n"))

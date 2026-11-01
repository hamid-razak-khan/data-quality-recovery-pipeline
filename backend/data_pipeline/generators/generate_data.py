"""
Synthetic Data Generator for E-Commerce Order Management.
Generates:
1. customers.csv (Customers Master)
2. orders.csv (Orders with controlled, reproducible invalid records)
"""
import os
import random
import csv
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple


class SyntheticDataGenerator:
    PRODUCT_NAMES = [
        "Mechanical Keyboard RGB",
        "Wireless Ergonomic Mouse",
        "Ultra HD 4K Monitor 27-inch",
        "Noise Cancelling Headphones",
        "USB-C Multiport Hub",
        "Laptop Stand Aluminum",
        "Gaming Desk Mat XL",
        "Smart LED Desk Lamp",
        "Webcam 1080p with Privacy Shutter",
        "Bluetooth Speaker Portable",
    ]

    ALLOWED_STATUSES = ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED", "CANCELLED"]
    INVALID_STATUSES = ["COMPLETED", "IN_TRANSIT", "RETURNED", "UNKNOWN", "ERROR"]

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)

    def generate_customers(self, count: int = 500) -> List[Dict[str, Any]]:
        """Generates list of customers."""
        random.seed(self.seed)
        first_names = ["James", "Emma", "Liam", "Olivia", "Noah", "Ava", "Lucas", "Sophia", "Oliver", "Isabella"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]

        customers = []
        base_date = datetime(2022, 1, 1)

        for i in range(1, count + 1):
            cust_id = f"CUST-{i:05d}"
            fname = random.choice(first_names)
            lname = random.choice(last_names)
            name = f"{fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}{i}@example.com"
            reg_date = (base_date + timedelta(days=random.randint(0, 1000))).strftime("%Y-%m-%d")
            status = "ACTIVE" if random.random() > 0.1 else "INACTIVE"

            customers.append({
                "customer_id": cust_id,
                "customer_name": name,
                "email": email,
                "registration_date": reg_date,
                "status": status,
            })
        return customers

    def generate_orders(
        self,
        record_count: int = 1000,
        customer_ids: List[str] = None,
        invalid_ratio: float = 0.10
    ) -> List[Dict[str, Any]]:
        """
        Generates orders with a controlled percentage of invalid records.
        """
        random.seed(self.seed)
        if not customer_ids:
            customer_ids = [f"CUST-{i:05d}" for i in range(1, 101)]

        orders = []
        base_date = datetime(2024, 1, 1)

        # Invalidation types distribution
        invalid_types = [
            "missing_customer_id",
            "missing_order_id",
            "invalid_fk",
            "negative_price",
            "zero_quantity",
            "calculation_mismatch",
            "invalid_status",
            "malformed_date",
            "duplicate_order_id",
            "null_product",
        ]

        seen_order_ids = []

        for i in range(1, record_count + 1):
            order_id = f"ORD-{i:06d}"
            customer_id = random.choice(customer_ids)
            product_name = random.choice(self.PRODUCT_NAMES)
            quantity = random.randint(1, 10)
            unit_price = Decimal(str(random.randint(1500, 49900) / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_amount = (Decimal(quantity) * unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            order_dt = base_date + timedelta(days=random.randint(0, 300), hours=random.randint(0, 23), minutes=random.randint(0, 59))
            order_date = order_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            order_status = random.choice(self.ALLOWED_STATUSES)

            # Check if this record should be invalid
            is_invalid = random.random() < invalid_ratio

            if is_invalid:
                inv_type = random.choice(invalid_types)

                if inv_type == "missing_customer_id":
                    customer_id = ""
                elif inv_type == "missing_order_id":
                    order_id = ""
                elif inv_type == "invalid_fk":
                    customer_id = f"NONEXISTENT-{random.randint(9000, 9999)}"
                elif inv_type == "negative_price":
                    unit_price = Decimal("-19.99")
                    total_amount = (Decimal(quantity) * unit_price).quantize(Decimal("0.01"))
                elif inv_type == "zero_quantity":
                    quantity = 0
                    total_amount = Decimal("0.00")
                elif inv_type == "calculation_mismatch":
                    # Deliberately distort total
                    total_amount = total_amount + Decimal("15.50")
                elif inv_type == "invalid_status":
                    order_status = random.choice(self.INVALID_STATUSES)
                elif inv_type == "malformed_date":
                    order_date = "invalid-date-99/99/9999"
                elif inv_type == "duplicate_order_id" and seen_order_ids:
                    order_id = random.choice(seen_order_ids)
                elif inv_type == "null_product":
                    product_name = ""

            if order_id:
                seen_order_ids.append(order_id)

            orders.append({
                "order_id": order_id,
                "customer_id": customer_id,
                "product_name": product_name,
                "quantity": quantity,
                "unit_price": str(unit_price),
                "total_amount": str(total_amount),
                "order_date": order_date,
                "order_status": order_status,
            })

        return orders

    @classmethod
    def write_csv(cls, records: List[Dict[str, Any]], output_path: str):
        """Writes dicts to CSV."""
        if not records:
            return
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        fieldnames = list(records[0].keys())
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    @classmethod
    def write_json(cls, records: List[Dict[str, Any]], output_path: str):
        """Writes dicts to JSON."""
        import json
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

    @classmethod
    def generate(
        cls,
        record_count: int = 1000,
        seed: int = 42,
        invalid_ratio: float = 0.10,
        output_dir: str = 'sample_data'
    ) -> Tuple[str, int]:
        """Convenience method for generating synthetic customers and orders."""
        gen = cls(seed=seed)
        customers = gen.generate_customers(count=max(50, min(500, record_count // 5)))
        cust_path = os.path.join(output_dir, "customers.csv")
        cls.write_csv(customers, cust_path)

        cust_ids = [c["customer_id"] for c in customers]
        orders = gen.generate_orders(record_count=record_count, customer_ids=cust_ids, invalid_ratio=invalid_ratio)
        out_path = os.path.join(output_dir, f"orders_{record_count}.csv")
        cls.write_csv(orders, out_path)
        return out_path, len(orders)

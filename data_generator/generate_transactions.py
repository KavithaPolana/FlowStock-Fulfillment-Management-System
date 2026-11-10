
import random
import sys
from pathlib import Path
from datetime import date, timedelta

# Import database connection
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.append(str(backend_path))

from database.db import get_connection

random.seed(20261022)

# Sample destinations
locations = [
    ("Hyderabad", "ZONE-1"),
    ("Vijayawada", "ZONE-2"),
    ("Chennai", "ZONE-3"),
    ("Bangalore", "ZONE-4"),
    ("Mumbai", "ZONE-5"),
    ("Delhi", "ZONE-1"),
    ("Pune", "ZONE-2"),
    ("Kolkata", "ZONE-3"),
    ("Visakhapatnam", "ZONE-4"),
    ("Coimbatore", "ZONE-5")
]

# Generate 100 orders
orders = []
order_lines = []

today = date.today()

for i in range(1, 101):

    order_id = f"ORD-2026-{i:06d}"
    customer_id = f"CUST-{random.randint(1, 50):04d}"

    destination_city, destination_zone = random.choice(locations)

    order_date = today - timedelta(days=random.randint(0, 30))

    orders.append((
        order_id,
        customer_id,
        order_date,
        destination_city,
        destination_zone,
        "NEW"
    ))

    # Each order contains 1 to 3 different products
    selected_skus = random.sample(range(1, 21), random.randint(1, 3))

    for sku_number in selected_skus:

        sku_id = f"SKU-{sku_number:04d}"
        quantity = random.randint(1, 5)
        unit_price = round(random.uniform(100, 2000), 2)

        order_lines.append((
            order_id,
            sku_id,
            quantity,
            unit_price
        ))

# Generate inventory for 20 warehouses x 20 SKUs
inventory = []

for node_number in range(1, 21):

    node_id = f"FUL-2026-{node_number:06d}"

    for sku_number in range(1, 21):

        sku_id = f"SKU-{sku_number:04d}"
        stock = random.randint(20, 200)

        inventory.append((
            node_id,
            sku_id,
            stock,
            0
        ))

# Insert into MySQL
connection = get_connection()

if connection:

    cursor = connection.cursor()

    try:

        # Insert orders
        cursor.executemany("""
            INSERT INTO orders
            (order_id, customer_id, order_date,
             destination_city, destination_zone, order_status)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                customer_id = VALUES(customer_id),
                order_date = VALUES(order_date),
                destination_city = VALUES(destination_city),
                destination_zone = VALUES(destination_zone),
                order_status = VALUES(order_status)
        """, orders)

        # Insert order lines
        cursor.executemany("""
            INSERT INTO order_lines
            (order_id, sku_id, quantity, unit_price)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                quantity = VALUES(quantity),
                unit_price = VALUES(unit_price)
        """, order_lines)

        # Insert warehouse inventory
        cursor.executemany("""
            INSERT INTO inventory
            (node_id, sku_id, available_quantity, reserved_quantity)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                available_quantity = VALUES(available_quantity),
                reserved_quantity = VALUES(reserved_quantity)
        """, inventory)

        connection.commit()

        print("Transaction data inserted successfully!")
        print("Orders:", len(orders))
        print("Order Lines:", len(order_lines))
        print("Inventory Records:", len(inventory))

    except Exception as error:

        connection.rollback()
        print("Insertion failed:", error)

    finally:
        cursor.close()
        connection.close()

else:
    print("Database connection failed!")


import sys
import random
from pathlib import Path
from datetime import date

backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

from database.db import get_connection

random.seed(20261022)

connection = get_connection()

if connection:
    cursor = connection.cursor()

    try:
        capacity_records = []

        for i in range(1, 21):

            node_id = f"FUL-2026-{i:06d}"

            max_orders = random.randint(40, 100)

            capacity_records.append((
                node_id,
                date.today(),
                max_orders,
                0
            ))

        cursor.executemany("""
            INSERT INTO warehouse_capacity
            (node_id, capacity_date, max_orders, allocated_orders)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                max_orders = VALUES(max_orders)
        """, capacity_records)

        connection.commit()

        print("Warehouse capacity created successfully!")
        print("Total warehouse capacity records:", len(capacity_records))

    except Exception as error:
        connection.rollback()
        print("Error:", error)

    finally:
        cursor.close()
        connection.close()

else:
    print("Database connection failed!")

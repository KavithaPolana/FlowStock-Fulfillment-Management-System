import random
import sys
from pathlib import Path

# Allow generator to import the backend database connection
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.append(str(backend_path))

from database.db import get_connection

random.seed(20261022)

# City and state mapping
locations = [
    ("Hyderabad", "Telangana"),
    ("Vijayawada", "Andhra Pradesh"),
    ("Chennai", "Tamil Nadu"),
    ("Bangalore", "Karnataka"),
    ("Mumbai", "Maharashtra"),
    ("Delhi", "Delhi"),
    ("Pune", "Maharashtra"),
    ("Kolkata", "West Bengal"),
    ("Visakhapatnam", "Andhra Pradesh"),
    ("Coimbatore", "Tamil Nadu")
]

# Generate 20 warehouses
nodes = []

for i in range(1, 21):
    city, state = random.choice(locations)

    nodes.append((
        f"FUL-2026-{i:06d}",
        f"Warehouse {i}",
        city,
        state,
        f"ZONE-{random.randint(1, 5)}"
    ))

# Generate 10 carriers
carriers = []

for i in range(1, 11):
    carriers.append((
        f"CAR-{i:03d}",
        f"Carrier {i}"
    ))

# Generate 20 SKUs
skus = []

for i in range(1, 21):
    skus.append((
        f"SKU-{i:04d}",
        f"Product {i}",
        random.choice(["Electronics", "Clothing", "Home"]),
        round(random.uniform(0.1, 5.0), 2)
    ))

# Connect to MySQL
connection = get_connection()

if connection:
    cursor = connection.cursor()

    try:
        # Insert SKUs
        cursor.executemany("""
            INSERT INTO skus
            (sku_id, sku_name, category, unit_weight)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                sku_name = VALUES(sku_name),
                category = VALUES(category),
                unit_weight = VALUES(unit_weight)
        """, skus)

        # Insert warehouses
        cursor.executemany("""
            INSERT INTO fulfillment_nodes
            (node_id, node_name, city, state, service_zone)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                node_name = VALUES(node_name),
                city = VALUES(city),
                state = VALUES(state),
                service_zone = VALUES(service_zone)
        """, nodes)

        # Insert carriers
        cursor.executemany("""
            INSERT INTO carriers
            (carrier_id, carrier_name)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                carrier_name = VALUES(carrier_name)
        """, carriers)

        connection.commit()

        print("Master data inserted successfully!")
        print("Warehouses:", len(nodes))
        print("Carriers:", len(carriers))
        print("SKUs:", len(skus))

    except Exception as error:
        connection.rollback()
        print("Insertion failed:", error)

    finally:
        cursor.close()
        connection.close()

else:
    print("Could not connect to MySQL.")
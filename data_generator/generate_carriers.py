import sys
from pathlib import Path
from datetime import date, timedelta, time

# Add backend folder to Python path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

from database.db import get_connection

connection = get_connection()

if connection is None:
    print("Database connection failed!")
    raise SystemExit(1)

cursor = connection.cursor()

try:
    # 1. Create delivery service levels
    services = [
        ("SVC-001", "Standard", 4),
        ("SVC-002", "Express", 2),
        ("SVC-003", "Economy", 6)
    ]

    cursor.executemany("""
        INSERT INTO service_levels
        (service_level_id, service_name, transit_days)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            service_name = VALUES(service_name),
            transit_days = VALUES(transit_days)
    """, services)

    # 2. Map carriers to service zones
    zone_records = []

    for carrier_number in range(1, 11):
        carrier_id = f"CAR-{carrier_number:03d}"

        # Each carrier covers 3 different zones
        supported_zones = [
            f"ZONE-{((carrier_number + offset - 2) % 5) + 1}"
            for offset in range(3)
        ]

        for zone in supported_zones:
            for service_id in ["SVC-001", "SVC-002"]:
                zone_records.append(
                    (carrier_id, service_id, zone)
                )

            # Some carriers also provide Economy
            if carrier_number % 2 == 0:
                zone_records.append(
                    (carrier_id, "SVC-003", zone)
                )

    cursor.executemany("""
        INSERT INTO carrier_service_zones
        (carrier_id, service_level_id, service_zone)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            service_zone = VALUES(service_zone)
    """, zone_records)

    # 3. Create carrier operating calendars for 30 days
    calendar_records = []
    today = date.today()

    cutoff_times = [
        time(15, 0),
        time(16, 0),
        time(17, 0),
        time(18, 0)
    ]

    for carrier_number in range(1, 11):
        carrier_id = f"CAR-{carrier_number:03d}"
        cutoff = cutoff_times[(carrier_number - 1) % 4]

        for day_number in range(30):
            operating_date = today + timedelta(days=day_number)

            # Sunday is a non-operating day
            is_operating = operating_date.weekday() != 6

            calendar_records.append((
                carrier_id,
                operating_date,
                is_operating,
                cutoff
            ))

    cursor.executemany("""
        INSERT INTO carrier_calendar
        (carrier_id, operating_date, is_operating, cutoff_time)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            is_operating = VALUES(is_operating),
            cutoff_time = VALUES(cutoff_time)
    """, calendar_records)

    connection.commit()

    print("Carrier setup completed successfully!")
    print("Service levels:", len(services))
    print("Carrier-zone-service mappings:", len(zone_records))
    print("Carrier calendar records:", len(calendar_records))

except Exception as error:
    connection.rollback()
    print("Error:", error)

finally:
    cursor.close()
    connection.close()
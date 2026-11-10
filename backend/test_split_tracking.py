
from datetime import datetime, timedelta

from services.tracking_engine import add_tracking_event


shipments = [
    "SHP-2026-000015-001",
    "SHP-2026-000015-002",
    "SHP-2026-000015-003"
]

tracking_journey = [
    ("CREATED", "Warehouse Dispatch Center"),
    ("PICKED_UP", "Carrier Pickup Hub"),
    ("IN_TRANSIT", "Transit Hub"),
    ("OUT_FOR_DELIVERY", "Local Delivery Center"),
    ("DELIVERED", "Customer Delivery Address")
]

start_time = datetime(2026, 11, 10, 12, 0, 0)

print("Starting split shipment tracking test...")

for shipment_index, shipment_id in enumerate(shipments):

    print("\nTracking shipment:", shipment_id)

    for event_index, (event_type, location) in enumerate(tracking_journey):

        event_time = start_time + timedelta(
            hours=shipment_index * 24 + event_index * 2
        )

        result = add_tracking_event(
            shipment_id,
            event_type,
            event_time,
            location
        )

        print(event_type, ":", result)

        if not result["success"]:
            print("Tracking stopped because of an error.")
            break

    else:
        print("Shipment tracking completed.")

print("\nSplit shipment tracking test finished.")

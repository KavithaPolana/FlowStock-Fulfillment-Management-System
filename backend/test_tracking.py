from datetime import datetime
from services.tracking_engine import add_tracking_event

result = add_tracking_event(
    shipment_id="SHP-2026-000001",
    event_type="DELIVERED",
    event_time=datetime(2026, 11, 11, 14, 30),
    location="Customer Delivery Address - Hyderabad"
)

print("\nTracking Result:")
print(result)
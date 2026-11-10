
from services.shipment_engine import create_shipment

order_id = "ORD-2026-000015"

print("Starting split shipment test...")
print("Order ID:", order_id)

result = create_shipment(order_id)

print("\nShipment Result:")
print(result)

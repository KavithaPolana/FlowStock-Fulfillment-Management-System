from services.fulfillment_engine import allocate_order

order_id = "ORD-2026-000015"

print("Starting split allocation test...")
print("Order ID:", order_id)

result = allocate_order(order_id)

print("\nAllocation Result:")
print(result)
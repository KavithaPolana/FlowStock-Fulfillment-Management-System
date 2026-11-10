from services.fulfillment_engine import allocate_order
from database.db import get_connection

# Get the first order from MySQL
connection = get_connection()
cursor = connection.cursor()

cursor.execute("""
    SELECT order_id
    FROM orders
    ORDER BY order_id
    LIMIT 1
""")

result = cursor.fetchone()

cursor.close()
connection.close()

if result:
    order_id = result[0]

    print("Testing Order:", order_id)

    allocation_result = allocate_order(order_id)

    print("\nAllocation Result:")
    print(allocation_result)

else:
    print("No orders found!")
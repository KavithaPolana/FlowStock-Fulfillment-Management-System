
from database.db import get_connection

connection = get_connection()

if connection is None:
    print("Database connection failed!")
    raise SystemExit(1)

cursor = connection.cursor()

try:
    order_id = "ORD-2026-000001"

    cursor.execute("""
        SELECT
            COUNT(*),
            SUM(
                CASE
                    WHEN shipment_status = 'DELIVERED'
                    THEN 1 ELSE 0
                END
            )
        FROM shipments
        WHERE order_id = %s
    """, (order_id,))

    total, delivered = cursor.fetchone()

    if total > 0 and total == delivered:

        cursor.execute("""
            UPDATE orders
            SET order_status = 'DELIVERED'
            WHERE order_id = %s
        """, (order_id,))

        connection.commit()

        print("Order status updated successfully!")
        print("Order ID:", order_id)
        print("Status: DELIVERED")

    else:
        print("Some shipments are still pending.")

except Exception as error:
    connection.rollback()
    print("Error:", error)

finally:
    cursor.close()
    connection.close()

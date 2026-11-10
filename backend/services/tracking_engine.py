
from database.db import get_connection


ALLOWED_TRANSITIONS = {
    "CREATED": "PICKED_UP",
    "PICKED_UP": "IN_TRANSIT",
    "IN_TRANSIT": "OUT_FOR_DELIVERY",
    "OUT_FOR_DELIVERY": "DELIVERED"
}


def add_tracking_event(shipment_id, event_type, event_time, location):

    connection = get_connection()

    if connection is None:
        return {
            "success": False,
            "message": "Database connection failed"
        }

    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Lock and fetch shipment
        cursor.execute("""
            SELECT *
            FROM shipments
            WHERE shipment_id = %s
            FOR UPDATE
        """, (shipment_id,))

        shipment = cursor.fetchone()

        if not shipment:
            raise ValueError("Shipment not found")

        # 2. Fetch the latest tracking event
        cursor.execute("""
            SELECT event_sequence, event_type, event_time
            FROM tracking_events
            WHERE shipment_id = %s
            ORDER BY event_sequence DESC
            LIMIT 1
        """, (shipment_id,))

        latest_event = cursor.fetchone()

        if latest_event:
            expected_event = ALLOWED_TRANSITIONS.get(
                latest_event["event_type"]
            )
            sequence = latest_event["event_sequence"] + 1
            previous_time = latest_event["event_time"]
        else:
            expected_event = "CREATED"
            sequence = 1
            previous_time = None

        # 3. Validate event transition
        if event_type != expected_event:
            raise ValueError(
                f"Invalid event. Expected: {expected_event}"
            )

        # 4. Validate event chronology
        if previous_time and event_time < previous_time:
            raise ValueError(
                "Event time cannot be before previous event"
            )

        dispatch_date = shipment["dispatch_date"]

        if hasattr(dispatch_date, "date"):
            dispatch_date = dispatch_date.date()

        if (
            event_type != "CREATED"
            and event_time.date() < dispatch_date
        ):
            raise ValueError(
                "Tracking event cannot occur before dispatch"
            )

        # 5. Generate tracking event ID
        tracking_event_id = (
            f"TRK-{shipment_id}-{sequence:03d}"
        )

        # 6. Insert tracking event
        cursor.execute("""
            INSERT INTO tracking_events (
                tracking_event_id,
                shipment_id,
                event_sequence,
                event_type,
                event_time,
                event_location
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            tracking_event_id,
            shipment_id,
            sequence,
            event_type,
            event_time,
            location
        ))

        # 7. Update shipment status
        if event_type == "DELIVERED":
            cursor.execute("""
                UPDATE shipments
                SET shipment_status = %s,
                    actual_delivery_date = %s
                WHERE shipment_id = %s
            """, (
                event_type,
                event_time.date(),
                shipment_id
            ))
        else:
            cursor.execute("""
                UPDATE shipments
                SET shipment_status = %s
                WHERE shipment_id = %s
            """, (
                event_type,
                shipment_id
            ))

        # 8. Lock parent order
        cursor.execute("""
            SELECT order_id
            FROM orders
            WHERE order_id = %s
            FOR UPDATE
        """, (shipment["order_id"],))

        # IMPORTANT: Fetch the locked order row
        order = cursor.fetchone()

        if not order:
            raise ValueError("Parent order not found")

        # 9. Count delivered shipments
        cursor.execute("""
            SELECT
                COUNT(*) AS total_shipments,
                SUM(
                    CASE
                        WHEN shipment_status = 'DELIVERED'
                        THEN 1
                        ELSE 0
                    END
                ) AS delivered_shipments
            FROM shipments
            WHERE order_id = %s
        """, (shipment["order_id"],))

        summary = cursor.fetchone()

        total_shipments = summary["total_shipments"]
        delivered_shipments = summary["delivered_shipments"] or 0

        # 10. Update parent order only when all shipments arrive
        order_delivered = (
            total_shipments > 0
            and total_shipments == delivered_shipments
        )

        if order_delivered:
            cursor.execute("""
                UPDATE orders
                SET order_status = 'DELIVERED'
                WHERE order_id = %s
            """, (shipment["order_id"],))

        # 11. Commit transaction
        connection.commit()

        return {
            "success": True,
            "tracking_event_id": tracking_event_id,
            "shipment_id": shipment_id,
            "event_type": event_type,
            "event_sequence": sequence,
            "delivered_shipments": delivered_shipments,
            "total_shipments": total_shipments,
            "order_delivered": order_delivered,
            "message": "Tracking event saved successfully"
        }

    except Exception as error:
        connection.rollback()

        return {
            "success": False,
            "message": str(error)
        }

    finally:
        cursor.close()
        connection.close()

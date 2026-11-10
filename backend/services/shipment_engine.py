
from database.db import get_connection
from datetime import date, datetime, timedelta


def create_shipment(order_id):

    connection = get_connection()

    if connection is None:
        return {
            "success": False,
            "message": "Database connection failed"
        }

    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Get order details
        cursor.execute("""
            SELECT *
            FROM orders
            WHERE order_id = %s
            FOR UPDATE
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            raise Exception("Order not found")

        if order["order_status"] != "ALLOCATED":
            raise Exception(
                "Order must be allocated before shipment creation"
            )

        # 2. Prevent duplicate shipment creation
        cursor.execute("""
            SELECT shipment_id
            FROM shipments
            WHERE order_id = %s
        """, (order_id,))

        if cursor.fetchone():
            raise Exception("Shipment already exists for this order")

        # 3. Read allocation details
        cursor.execute("""
            SELECT
                ad.decision_id,
                ad.node_id,
                n.node_name,
                n.city,
                al.order_line_id,
                al.allocated_quantity,
                ol.quantity AS ordered_quantity
            FROM allocation_decisions ad
            JOIN fulfillment_nodes n
                ON n.node_id = ad.node_id
            JOIN allocation_lines al
                ON al.decision_id = ad.decision_id
            JOIN order_lines ol
                ON ol.order_line_id = al.order_line_id
            WHERE ad.order_id = %s
              AND ad.decision_status = 'ALLOCATED'
            ORDER BY ad.node_id, al.order_line_id
        """, (order_id,))

        allocation_rows = cursor.fetchall()

        if not allocation_rows:
            raise Exception("No saved allocation quantities found")

        # 4. Group allocations by warehouse
        warehouse_allocations = {}
        allocated_totals = {}

        for row in allocation_rows:

            node_id = row["node_id"]

            if node_id not in warehouse_allocations:
                warehouse_allocations[node_id] = {
                    "node_name": row["node_name"],
                    "city": row["city"],
                    "lines": []
                }

            warehouse_allocations[node_id]["lines"].append({
                "order_line_id": row["order_line_id"],
                "allocated_quantity": row["allocated_quantity"]
            })

            line_id = row["order_line_id"]

            allocated_totals[line_id] = (
                allocated_totals.get(line_id, 0)
                + row["allocated_quantity"]
            )

        # 5. Validate complete allocation
        cursor.execute("""
            SELECT order_line_id, quantity
            FROM order_lines
            WHERE order_id = %s
        """, (order_id,))

        order_lines = cursor.fetchall()

        for line in order_lines:

            allocated = allocated_totals.get(
                line["order_line_id"], 0
            )

            if allocated != line["quantity"]:
                raise Exception(
                    f"Allocation mismatch for order line "
                    f"{line['order_line_id']}. "
                    f"Ordered: {line['quantity']}, allocated: {allocated}"
                )

        # 6. Prepare shipment IDs
        base_shipment_id = order_id.replace("ORD-", "SHP-", 1)

        warehouse_ids = sorted(warehouse_allocations.keys())
        total_warehouses = len(warehouse_ids)

        today = date.today()
        current_time = datetime.now().time()

        created_shipments = []

        # 7. Create one shipment per warehouse
        for index, node_id in enumerate(warehouse_ids, start=1):

            warehouse = warehouse_allocations[node_id]

            if total_warehouses == 1:
                shipment_id = base_shipment_id
                promise_suffix = "01"
            else:
                shipment_id = f"{base_shipment_id}-{index:03d}"
                promise_suffix = f"{index:02d}"

            # 8. Find eligible carrier and service
            cursor.execute("""
                SELECT
                    c.carrier_id,
                    c.carrier_name,
                    sl.service_level_id,
                    sl.service_name,
                    sl.transit_days,
                    cc.operating_date AS dispatch_date,
                    cc.cutoff_time
                FROM carrier_service_zones csz
                JOIN carriers c
                    ON c.carrier_id = csz.carrier_id
                JOIN service_levels sl
                    ON sl.service_level_id = csz.service_level_id
                JOIN carrier_calendar cc
                    ON cc.carrier_id = csz.carrier_id
                WHERE csz.service_zone = %s
                  AND c.is_active = TRUE
                  AND cc.is_operating = TRUE
                  AND cc.operating_date >= %s
                  AND (
                      cc.operating_date > %s
                      OR cc.cutoff_time >= %s
                  )
                ORDER BY
                    sl.transit_days ASC,
                    cc.operating_date ASC,
                    c.carrier_id ASC
                LIMIT 1
            """, (
                order["destination_zone"],
                today,
                today,
                current_time
            ))

            carrier = cursor.fetchone()

            if not carrier:
                raise Exception(
                    f"No eligible carrier found for warehouse "
                    f"{node_id} and destination zone "
                    f"{order['destination_zone']}"
                )

            # 9. Calculate delivery promise
            dispatch_date = carrier["dispatch_date"]

            promised_date = (
                dispatch_date
                + timedelta(days=carrier["transit_days"])
            )

            # 10. Insert shipment
            cursor.execute("""
                INSERT INTO shipments (
                    shipment_id,
                    order_id,
                    node_id,
                    carrier_id,
                    service_level_id,
                    dispatch_date,
                    actual_delivery_date,
                    shipment_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                shipment_id,
                order_id,
                node_id,
                carrier["carrier_id"],
                carrier["service_level_id"],
                dispatch_date,
                None,
                "CREATED"
            ))

            # 11. Automatically insert initial CREATED tracking event
            tracking_event_id = f"TRK-{shipment_id}-001"

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
                1,
                "CREATED",
                datetime.now(),
                warehouse["city"]
            ))

            # 12. Attach allocated product quantities
            for line in warehouse["lines"]:

                cursor.execute("""
                    INSERT INTO shipment_lines (
                        shipment_id,
                        order_line_id,
                        allocated_quantity
                    )
                    VALUES (%s, %s, %s)
                """, (
                    shipment_id,
                    line["order_line_id"],
                    line["allocated_quantity"]
                ))

            # 13. Save delivery promise
            promise_id = f"PROM-{order_id}-{promise_suffix}"

            cursor.execute("""
                INSERT INTO delivery_promises (
                    promise_id,
                    order_id,
                    shipment_id,
                    promised_delivery_date,
                    promise_version
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                promise_id,
                order_id,
                shipment_id,
                promised_date,
                1
            ))

            created_shipments.append({
                "shipment_id": shipment_id,
                "warehouse_id": node_id,
                "warehouse": warehouse["node_name"],
                "city": warehouse["city"],
                "carrier": carrier["carrier_name"],
                "service": carrier["service_name"],
                "dispatch_date": str(dispatch_date),
                "promised_delivery_date": str(promised_date),
                "products": warehouse["lines"]
            })

        connection.commit()

        return {
            "success": True,
            "order_id": order_id,
            "total_shipments": len(created_shipments),
            "shipments": created_shipments,
            "message": (
                "Shipments, initial tracking events and "
                "delivery promises created successfully"
            )
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

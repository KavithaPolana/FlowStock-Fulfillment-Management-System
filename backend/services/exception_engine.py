
from database.db import get_connection


def detect_exceptions():

    connection = get_connection()

    if connection is None:
        return {
            "success": False,
            "message": "Database connection failed"
        }

    cursor = connection.cursor(dictionary=True)

    checks = [

        {
            "name": "LATE_DELIVERY",
            "sql": """
                SELECT
                    s.order_id,
                    s.shipment_id,
                    'LATE_DELIVERY' AS issue_type,
                    'HIGH' AS severity,
                    CONCAT(
                        'Shipment ',
                        s.shipment_id,
                        ' was delivered on ',
                        s.actual_delivery_date,
                        ' after promised date ',
                        dp.promised_delivery_date
                    ) AS description
                FROM shipments s
                JOIN delivery_promises dp
                    ON dp.shipment_id = s.shipment_id
                WHERE s.actual_delivery_date >
                      dp.promised_delivery_date
            """
        },

        {
            "name": "UNSUPPORTED_CARRIER_ZONE",
            "sql": """
                SELECT
                    o.order_id,
                    s.shipment_id,
                    'UNSUPPORTED_CARRIER_ZONE' AS issue_type,
                    'HIGH' AS severity,
                    CONCAT(
                        'Carrier does not support service zone ',
                        o.destination_zone
                    ) AS description
                FROM shipments s
                JOIN orders o
                    ON o.order_id = s.order_id
                WHERE s.carrier_id IS NOT NULL
                  AND s.service_level_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1
                      FROM carrier_service_zones csz
                      WHERE csz.carrier_id = s.carrier_id
                        AND csz.service_level_id =
                            s.service_level_id
                        AND csz.service_zone =
                            o.destination_zone
                  )
            """
        },

        {
            "name": "DELIVERED_BEFORE_DISPATCH",
            "sql": """
                SELECT
                    s.order_id,
                    s.shipment_id,
                    'DELIVERED_BEFORE_DISPATCH' AS issue_type,
                    'CRITICAL' AS severity,
                    'Shipment delivery occurred before dispatch'
                        AS description
                FROM shipments s
                WHERE (
                    s.actual_delivery_date IS NOT NULL
                    AND s.actual_delivery_date <
                        DATE(s.dispatch_date)
                )
                OR EXISTS (
                    SELECT 1
                    FROM tracking_events te
                    WHERE te.shipment_id = s.shipment_id
                      AND te.event_type = 'DELIVERED'
                      AND te.event_time < s.dispatch_date
                )
            """
        },

        {
            "name": "ALLOCATION_EXCEEDS_STOCK",
            "sql": """
                SELECT
                    NULL AS order_id,
                    NULL AS shipment_id,
                    'ALLOCATION_EXCEEDS_STOCK' AS issue_type,
                    'CRITICAL' AS severity,
                    CONCAT(
                        'Allocated quantity for node ',
                        totals.node_id,
                        ', SKU ',
                        totals.sku_id,
                        ' is ',
                        totals.allocated_quantity,
                        ', but reserved inventory is ',
                        COALESCE(i.reserved_quantity, 0)
                    ) AS description
                FROM (
                    SELECT
                        d.node_id,
                        ol.sku_id,
                        SUM(al.allocated_quantity)
                            AS allocated_quantity
                    FROM allocation_lines al
                    JOIN allocation_decisions d
                        ON d.decision_id = al.decision_id
                    JOIN order_lines ol
                        ON ol.order_line_id = al.order_line_id
                    GROUP BY d.node_id, ol.sku_id
                ) totals
                LEFT JOIN inventory i
                    ON i.node_id = totals.node_id
                   AND i.sku_id = totals.sku_id
                WHERE totals.allocated_quantity >
                      COALESCE(i.reserved_quantity, 0)
            """
        },

        {
            "name": "SPLIT_STATUS_ROLLUP_MISMATCH",
            "sql": """
                SELECT
                    o.order_id,
                    NULL AS shipment_id,
                    'SPLIT_STATUS_ROLLUP_MISMATCH' AS issue_type,
                    'HIGH' AS severity,
                    CONCAT(
                        'Order status is ',
                        o.order_status,
                        '. Delivered shipments: ',
                        summary.delivered_shipments,
                        ' of ',
                        summary.total_shipments
                    ) AS description
                FROM orders o
                JOIN (
                    SELECT
                        order_id,
                        COUNT(*) AS total_shipments,
                        SUM(
                            CASE
                                WHEN shipment_status = 'DELIVERED'
                                THEN 1
                                ELSE 0
                            END
                        ) AS delivered_shipments
                    FROM shipments
                    GROUP BY order_id
                    HAVING COUNT(*) > 1
                ) summary
                    ON summary.order_id = o.order_id
                WHERE (
                    o.order_status = 'DELIVERED'
                    AND summary.delivered_shipments <
                        summary.total_shipments
                )
                OR (
                    summary.delivered_shipments =
                        summary.total_shipments
                    AND o.order_status <> 'DELIVERED'
                )
            """
        }
    ]

    total_detected = 0
    total_new = 0
    results = []

    try:

        for check in checks:

            cursor.execute(check["sql"])
            rows = cursor.fetchall()

            detected_count = len(rows)
            new_count = 0

            for row in rows:

                cursor.execute("""
                    INSERT INTO exceptions (
                        order_id,
                        shipment_id,
                        issue_type,
                        severity,
                        description,
                        detected_at
                    )
                    SELECT
                        %s, %s, %s, %s, %s, NOW()
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM exceptions
                        WHERE order_id <=> %s
                          AND shipment_id <=> %s
                          AND issue_type = %s
                    )
                """, (
                    row["order_id"],
                    row["shipment_id"],
                    row["issue_type"],
                    row["severity"],
                    row["description"],
                    row["order_id"],
                    row["shipment_id"],
                    row["issue_type"]
                ))

                new_count += cursor.rowcount

            total_detected += detected_count
            total_new += new_count

            results.append({
                "exception_type": check["name"],
                "detected": detected_count,
                "new_records": new_count
            })

        connection.commit()

        return {
            "success": True,
            "total_detected": total_detected,
            "total_new_records": total_new,
            "results": results,
            "message": "Exception detection completed"
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

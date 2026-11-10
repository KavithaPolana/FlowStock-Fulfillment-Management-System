
from datetime import datetime

from flask import Blueprint, jsonify, request

from database.db import get_connection
from services.fulfillment_engine import allocate_order
from services.shipment_engine import create_shipment
from services.tracking_engine import add_tracking_event
from services.exception_engine import detect_exceptions


fulfillment_bp = Blueprint("fulfillment", __name__)


def database_error():
    return jsonify({
        "success": False,
        "message": "Database connection failed"
    }), 500


# --------------------------------------------------
# 1. GET ALL ORDERS
# --------------------------------------------------

@fulfillment_bp.route("/orders", methods=["GET"])
def get_orders():

    connection = get_connection()

    if connection is None:
        return database_error()

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                o.order_id,
                o.customer_id,
                o.order_date,
                o.destination_city,
                o.destination_zone,
                o.order_status,
                COUNT(DISTINCT ol.order_line_id) AS total_order_lines,
                COALESCE(SUM(ol.quantity), 0) AS total_units
            FROM orders o
            LEFT JOIN order_lines ol
                ON ol.order_id = o.order_id
            GROUP BY
                o.order_id,
                o.customer_id,
                o.order_date,
                o.destination_city,
                o.destination_zone,
                o.order_status
            ORDER BY o.order_date DESC
        """)

        orders = cursor.fetchall()

        return jsonify({
            "success": True,
            "total_orders": len(orders),
            "orders": orders
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# 2. GET INDIVIDUAL ORDER DETAILS
# --------------------------------------------------

@fulfillment_bp.route("/orders/<order_id>", methods=["GET"])
def get_order_details(order_id):

    connection = get_connection()

    if connection is None:
        return database_error()

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT *
            FROM orders
            WHERE order_id = %s
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            return jsonify({
                "success": False,
                "message": "Order not found"
            }), 404

        cursor.execute("""
            SELECT
                ol.order_line_id,
                ol.sku_id,
                s.sku_name,
                s.category,
                ol.quantity,
                ol.unit_price
            FROM order_lines ol
            JOIN skus s ON s.sku_id = ol.sku_id
            WHERE ol.order_id = %s
        """, (order_id,))

        order_lines = cursor.fetchall()

        cursor.execute("""
            SELECT
                sh.shipment_id,
                sh.node_id,
                n.node_name,
                sh.carrier_id,
                c.carrier_name,
                sh.service_level_id,
                sl.service_name,
                sh.dispatch_date,
                sh.actual_delivery_date,
                sh.shipment_status
            FROM shipments sh
            LEFT JOIN fulfillment_nodes n
                ON n.node_id = sh.node_id
            LEFT JOIN carriers c
                ON c.carrier_id = sh.carrier_id
            LEFT JOIN service_levels sl
                ON sl.service_level_id = sh.service_level_id
            WHERE sh.order_id = %s
        """, (order_id,))

        shipments = cursor.fetchall()

        cursor.execute("""
            SELECT
                promise_id,
                shipment_id,
                promised_delivery_date,
                promise_version
            FROM delivery_promises
            WHERE order_id = %s
        """, (order_id,))

        promises = cursor.fetchall()

        return jsonify({
            "success": True,
            "order": order,
            "order_lines": order_lines,
            "shipments": shipments,
            "delivery_promises": promises
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# 3. ALLOCATE AN ORDER
# --------------------------------------------------

@fulfillment_bp.route(
    "/orders/<order_id>/allocate",
    methods=["POST"]
)
def allocate_order_api(order_id):

    try:
        result = allocate_order(order_id)

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


# --------------------------------------------------
# 4. CREATE SHIPMENTS FOR AN ORDER
# --------------------------------------------------

@fulfillment_bp.route(
    "/orders/<order_id>/shipments",
    methods=["POST"]
)
def create_shipments_api(order_id):

    try:
        result = create_shipment(order_id)

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


# --------------------------------------------------
# 5. GET ALL SHIPMENTS
# --------------------------------------------------

@fulfillment_bp.route("/shipments", methods=["GET"])
def get_shipments():

    connection = get_connection()

    if connection is None:
        return database_error()

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                sh.shipment_id,
                sh.order_id,
                sh.node_id,
                n.node_name,
                n.city AS warehouse_city,
                sh.carrier_id,
                c.carrier_name,
                sh.service_level_id,
                sl.service_name,
                sh.dispatch_date,
                sh.actual_delivery_date,
                sh.shipment_status,
                o.destination_city,
                o.destination_zone
            FROM shipments sh
            JOIN orders o
                ON o.order_id = sh.order_id
            LEFT JOIN fulfillment_nodes n
                ON n.node_id = sh.node_id
            LEFT JOIN carriers c
                ON c.carrier_id = sh.carrier_id
            LEFT JOIN service_levels sl
                ON sl.service_level_id = sh.service_level_id
            ORDER BY sh.dispatch_date DESC
        """)

        shipments = cursor.fetchall()

        return jsonify({
            "success": True,
            "total_shipments": len(shipments),
            "shipments": shipments
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# 6. GET TRACKING HISTORY
# --------------------------------------------------

@fulfillment_bp.route(
    "/shipments/<shipment_id>/tracking",
    methods=["GET"]
)
def get_tracking(shipment_id):

    connection = get_connection()

    if connection is None:
        return database_error()

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                tracking_event_id,
                shipment_id,
                event_sequence,
                event_type,
                event_time,
                event_location
            FROM tracking_events
            WHERE shipment_id = %s
            ORDER BY event_sequence ASC
        """, (shipment_id,))

        events = cursor.fetchall()

        return jsonify({
            "success": True,
            "shipment_id": shipment_id,
            "total_events": len(events),
            "tracking_events": events
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# 7. ADD TRACKING EVENT
# --------------------------------------------------

@fulfillment_bp.route("/tracking", methods=["POST"])
def add_tracking():

    data = request.get_json(silent=True) or {}

    required_fields = [
        "shipment_id",
        "event_type",
        "event_time",
        "location"
    ]

    missing_fields = [
        field for field in required_fields
        if not data.get(field)
    ]

    if missing_fields:
        return jsonify({
            "success": False,
            "message": "Missing required fields",
            "missing_fields": missing_fields
        }), 400

    try:
        event_time = datetime.fromisoformat(
            data["event_time"]
        )

        result = add_tracking_event(
            data["shipment_id"],
            data["event_type"].upper(),
            event_time,
            data["location"]
        )

        status_code = 200 if result.get("success") else 400

        return jsonify(result), status_code

    except ValueError as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 400

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


# --------------------------------------------------
# 8. GET ALL EXCEPTIONS
# --------------------------------------------------

@fulfillment_bp.route("/exceptions", methods=["GET"])
def get_exceptions():

    connection = get_connection()

    if connection is None:
        return database_error()

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                exception_id,
                order_id,
                shipment_id,
                issue_type,
                severity,
                description,
                detected_at
            FROM exceptions
            ORDER BY detected_at DESC
        """)

        exceptions = cursor.fetchall()

        return jsonify({
            "success": True,
            "total_exceptions": len(exceptions),
            "exceptions": exceptions
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# 9. RUN EXCEPTION DETECTION
# --------------------------------------------------

@fulfillment_bp.route(
    "/exceptions/detect",
    methods=["POST"]
)
def run_exception_detection():

    try:
        result = detect_exceptions()

        status_code = 200 if result.get("success") else 500

        return jsonify(result), status_code

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500


# --------------------------------------------------
# 10. GET WAREHOUSES
# --------------------------------------------------

@fulfillment_bp.route("/warehouses", methods=["GET"])
def get_warehouses():

    connection = get_connection()

    if connection is None:
        return database_error()

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                n.node_id,
                n.node_name,
                n.city,
                n.state,
                n.service_zone,
                n.is_active,
                COALESCE(wc.max_orders, 0) AS max_orders,
                COALESCE(wc.allocated_orders, 0)
                    AS allocated_orders
            FROM fulfillment_nodes n
            LEFT JOIN warehouse_capacity wc
                ON wc.node_id = n.node_id
                AND wc.capacity_date = CURDATE()
            ORDER BY n.node_id
        """)

        warehouses = cursor.fetchall()

        return jsonify({
            "success": True,
            "total_warehouses": len(warehouses),
            "warehouses": warehouses
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        connection.close()


# --------------------------------------------------
# 11. GET INVENTORY
# --------------------------------------------------

@fulfillment_bp.route("/inventory", methods=["GET"])
def get_inventory():

    connection = get_connection()

    if connection is None:
        return database_error()

    cursor = connection.cursor(dictionary=True)

    try:
        node_id = request.args.get("node_id")

        if node_id:
            cursor.execute("""
                SELECT
                    i.node_id,
                    n.node_name,
                    i.sku_id,
                    s.sku_name,
                    i.available_quantity,
                    i.reserved_quantity
                FROM inventory i
                JOIN fulfillment_nodes n
                    ON n.node_id = i.node_id
                JOIN skus s
                    ON s.sku_id = i.sku_id
                WHERE i.node_id = %s
                ORDER BY i.sku_id
            """, (node_id,))

        else:
            cursor.execute("""
                SELECT
                    i.node_id,
                    n.node_name,
                    i.sku_id,
                    s.sku_name,
                    i.available_quantity,
                    i.reserved_quantity
                FROM inventory i
                JOIN fulfillment_nodes n
                    ON n.node_id = i.node_id
                JOIN skus s
                    ON s.sku_id = i.sku_id
                ORDER BY i.node_id, i.sku_id
            """)

        inventory = cursor.fetchall()

        return jsonify({
            "success": True,
            "total_inventory_records": len(inventory),
            "inventory": inventory
        })

    except Exception as error:
        return jsonify({
            "success": False,
            "message": str(error)
        }), 500

    finally:
        cursor.close()
        connection.close()

from flask import Blueprint, jsonify
from database.db import get_connection

dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route("/dashboard", methods=["GET"])
def get_dashboard():

    connection = get_connection()

    if connection is None:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT COUNT(*) AS total_orders FROM orders")
        total_orders = cursor.fetchone()["total_orders"]

        cursor.execute("SELECT COUNT(*) AS total_nodes FROM fulfillment_nodes")
        total_nodes = cursor.fetchone()["total_nodes"]

        cursor.execute("SELECT COUNT(*) AS total_shipments FROM shipments")
        total_shipments = cursor.fetchone()["total_shipments"]

        cursor.execute("SELECT COUNT(*) AS total_exceptions FROM exceptions")
        total_exceptions = cursor.fetchone()["total_exceptions"]

        return jsonify({
            "total_orders": total_orders,
            "total_nodes": total_nodes,
            "total_shipments": total_shipments,
            "total_exceptions": total_exceptions
        })

    finally:
        cursor.close()
        connection.close()
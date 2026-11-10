from database.db import get_connection


def allocate_order(order_id):
    connection = get_connection()

    if connection is None:
        return {
            "success": False,
            "message": "Database connection failed"
        }

    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Lock the order so two requests cannot allocate it simultaneously.
        cursor.execute("""
            SELECT *
            FROM orders
            WHERE order_id = %s
            FOR UPDATE
        """, (order_id,))

        order = cursor.fetchone()

        if not order:
            return {
                "success": False,
                "message": "Order not found"
            }

        if order["order_status"] not in ("PENDING", "NEW"):
            return {
                "success": False,
                "message": (
                    f"Order cannot be allocated. Current status: "
                    f"{order['order_status']}"
                )
            }

        # 2. Prevent duplicate allocation records.
        cursor.execute("""
            SELECT decision_id
            FROM allocation_decisions
            WHERE order_id = %s
              AND decision_status = 'ALLOCATED'
            LIMIT 1
        """, (order_id,))

        if cursor.fetchone():
            return {
                "success": False,
                "message": "This order already has an allocation record"
            }

        # 3. Get order products.
        cursor.execute("""
            SELECT order_line_id, sku_id, quantity
            FROM order_lines
            WHERE order_id = %s
            ORDER BY order_line_id
        """, (order_id,))

        order_lines = cursor.fetchall()

        if not order_lines:
            return {
                "success": False,
                "message": "Order has no products"
            }

        sku_ids = list({line["sku_id"] for line in order_lines})
        placeholders = ", ".join(["%s"] * len(sku_ids))

        # 4. Lock active warehouses that have capacity today.
        cursor.execute("""
            SELECT
                n.node_id,
                n.node_name,
                n.city,
                w.max_orders,
                w.allocated_orders,
                (w.max_orders - w.allocated_orders) AS remaining_capacity
            FROM fulfillment_nodes n
            JOIN warehouse_capacity w
                ON w.node_id = n.node_id
            WHERE n.is_active = TRUE
              AND w.capacity_date = CURDATE()
              AND w.allocated_orders < w.max_orders
            ORDER BY n.node_id
            FOR UPDATE
        """)

        warehouse_rows = cursor.fetchall()

        if not warehouse_rows:
            return {
                "success": False,
                "message": "No active warehouse has capacity today"
            }

        warehouses = {}

        for row in warehouse_rows:
            warehouses[row["node_id"]] = {
                "node_name": row["node_name"],
                "city": row["city"],
                "remaining_capacity": row["remaining_capacity"],
                "inventory": {}
            }

        # 5. Lock inventory records for the required products.
        cursor.execute(f"""
            SELECT
                node_id,
                sku_id,
                available_quantity,
                reserved_quantity
            FROM inventory
            WHERE sku_id IN ({placeholders})
            ORDER BY node_id, sku_id
            FOR UPDATE
        """, tuple(sku_ids))

        inventory_rows = cursor.fetchall()

        for row in inventory_rows:
            node_id = row["node_id"]

            if node_id in warehouses:
                warehouses[node_id]["inventory"][row["sku_id"]] = (
                    row["available_quantity"] - row["reserved_quantity"]
                )

        # 6. Plan how much each warehouse will supply.
        # Structure:
        # node_id -> order_line_id -> allocated quantity
        node_allocations = {}

        for line in order_lines:
            remaining_quantity = line["quantity"]

            # Prefer warehouses with more available stock for this SKU.
            candidates = []

            for node_id, warehouse in warehouses.items():
                available = warehouse["inventory"].get(
                    line["sku_id"], 0
                )

                has_capacity = (
                    warehouse["remaining_capacity"] > 0
                    or node_id in node_allocations
                )

                if available > 0 and has_capacity:
                    candidates.append((node_id, available))

            candidates.sort(key=lambda item: (-item[1], item[0]))

            for node_id, available in candidates:
                if remaining_quantity <= 0:
                    break

                quantity_to_allocate = min(
                    remaining_quantity,
                    available
                )

                if node_id not in node_allocations:
                    node_allocations[node_id] = {}

                node_allocations[node_id][
                    line["order_line_id"]
                ] = quantity_to_allocate

                # Reduce in-memory stock so another line cannot reuse it.
                warehouses[node_id]["inventory"][line["sku_id"]] -= (
                    quantity_to_allocate
                )

                remaining_quantity -= quantity_to_allocate

            if remaining_quantity > 0:
                raise Exception(
                    f"Insufficient stock for SKU {line['sku_id']}. "
                    f"Short quantity: {remaining_quantity}"
                )

        if not node_allocations:
            raise Exception("No warehouse allocation could be planned")

        # 7. Save one allocation decision per selected warehouse.
        allocation_summary = []

        for node_id, line_allocations in node_allocations.items():
            total_units = sum(line_allocations.values())

            cursor.execute("""
                INSERT INTO allocation_decisions (
                    order_id,
                    node_id,
                    decision_status,
                    decision_score,
                    decision_reason
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                order_id,
                node_id,
                "ALLOCATED",
                1.0,
                (
                    f"Allocated {total_units} units across "
                    f"{len(line_allocations)} order lines"
                )
            ))

            decision_id = cursor.lastrowid

            # 8. Save the exact quantity supplied by this warehouse.
            for order_line_id, quantity in line_allocations.items():
                cursor.execute("""
                    INSERT INTO allocation_lines (
                        decision_id,
                        order_line_id,
                        allocated_quantity
                    )
                    VALUES (%s, %s, %s)
                """, (
                    decision_id,
                    order_line_id,
                    quantity
                ))

                # 9. Reserve inventory.
                cursor.execute("""
                    UPDATE inventory
                    SET reserved_quantity = reserved_quantity + %s
                    WHERE node_id = %s
                      AND sku_id = (
                          SELECT sku_id
                          FROM order_lines
                          WHERE order_line_id = %s
                      )
                      AND available_quantity - reserved_quantity >= %s
                """, (
                    quantity,
                    node_id,
                    order_line_id,
                    quantity
                ))

                if cursor.rowcount != 1:
                    raise Exception(
                        f"Inventory changed during allocation "
                        f"for warehouse {node_id}"
                    )

            # 10. Consume one order-capacity slot per warehouse used.
            cursor.execute("""
                UPDATE warehouse_capacity
                SET allocated_orders = allocated_orders + 1
                WHERE node_id = %s
                  AND capacity_date = CURDATE()
                  AND allocated_orders < max_orders
            """, (node_id,))

            if cursor.rowcount != 1:
                raise Exception(
                    f"Capacity unavailable for warehouse {node_id}"
                )

            allocation_summary.append({
                "warehouse_id": node_id,
                "warehouse": warehouses[node_id]["node_name"],
                "city": warehouses[node_id]["city"],
                "allocated_units": total_units
            })

        # 11. Mark the complete order as allocated.
        cursor.execute("""
            UPDATE orders
            SET order_status = 'ALLOCATED'
            WHERE order_id = %s
        """, (order_id,))

        connection.commit()

        return {
            "success": True,
            "order_id": order_id,
            "warehouses_used": len(allocation_summary),
            "allocations": allocation_summary,
            "message": "Order allocated successfully across warehouses"
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
"""
Safe benchmark-data generator for fulfillment-management-system.

Target totals:
- 50,000 orders
- 100,000 tracking events

Current database data is preserved. This script:
- Adds only the missing orders/events.
- Creates 1 shipment for each of the required new completed orders.
- Creates 5 chronological tracking events per new shipment.
- Reserves one unit of inventory per generated shipment.
- Increases warehouse capacity allocations.
- Inserts missing historical carrier-calendar/capacity rows only.
- Uses one database transaction; failures roll back all changes.

IMPORTANT:
1. Keep DRY_RUN = True for the first run.
2. Check the preview.
3. Change DRY_RUN = False and run again to save the data.
"""

import random
import sys
from pathlib import Path
from datetime import date, datetime, time, timedelta

# Add backend folder to Python path
backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))

from database.db import get_connection


# -------------------- SETTINGS --------------------

TARGET_ORDERS = 50_000
TARGET_TRACKING_EVENTS = 100_000
EVENTS_PER_NEW_SHIPMENT = 5

BATCH_SIZE = 1_000
DRY_RUN = False #se only after reviewing the dry-run output.

RANDOM_SEED = 20261110
random.seed(RANDOM_SEED)

DESTINATIONS = [
    ("Hyderabad", "ZONE-1"),
    ("Vijayawada", "ZONE-2"),
    ("Visakhapatnam", "ZONE-3"),
    ("Chennai", "ZONE-4"),
    ("Bengaluru", "ZONE-5"),
    ("Delhi", "ZONE-1"),
    ("Mumbai", "ZONE-2"),
    ("Pune", "ZONE-3"),
    ("Kolkata", "ZONE-4"),
    ("Kochi", "ZONE-5"),
]


# -------------------- HELPERS --------------------

def execute_batches(cursor, sql, records, batch_size=BATCH_SIZE):
    """Execute many rows in manageable batches."""
    for start in range(0, len(records), batch_size):
        cursor.executemany(sql, records[start:start + batch_size])


def get_count(cursor, table_name):
    # Table names are fixed constants in this script, not user input.
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    return cursor.fetchone()[0]


def get_next_order_number(cursor):
    cursor.execute("""
        SELECT order_id
        FROM orders
        WHERE order_id LIKE 'ORD-2026-%'
        ORDER BY order_id DESC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if not row:
        return 1

    last_id = row[0]
    try:
        return int(last_id.rsplit("-", 1)[1]) + 1
    except (ValueError, IndexError):
        raise RuntimeError(
            f"Cannot determine the next order number from {last_id!r}."
        )


def make_datetime(day_value, hour, minute=0):
    return datetime.combine(day_value, time(hour, minute))


# -------------------- MAIN GENERATOR --------------------

def main():
    connection = get_connection()

    if connection is None:
        print("Database connection failed.")
        return

    cursor = connection.cursor()

    try:
        # Start one transaction. Any error rolls back all generated records.
        connection.start_transaction()

        current_orders = get_count(cursor, "orders")
        current_events = get_count(cursor, "tracking_events")
        current_shipments = get_count(cursor, "shipments")

        orders_to_add = TARGET_ORDERS - current_orders
        events_to_add = TARGET_TRACKING_EVENTS - current_events

        print("\n========== CURRENT DATABASE ==========")
        print("Orders:", current_orders)
        print("Shipments:", current_shipments)
        print("Tracking events:", current_events)

        if orders_to_add < 0 or events_to_add < 0:
            raise RuntimeError(
                "The database already exceeds at least one target. "
                "No data has been changed."
            )

        if orders_to_add == 0 and events_to_add == 0:
            print("\nTargets are already reached. Nothing to generate.")
            connection.rollback()
            return

        if events_to_add % EVENTS_PER_NEW_SHIPMENT != 0:
            raise RuntimeError(
                f"{events_to_add} tracking events remain. This generator "
                f"creates {EVENTS_PER_NEW_SHIPMENT} events per shipment, "
                "so the remaining count must be divisible by 5."
            )

        shipments_to_add = events_to_add // EVENTS_PER_NEW_SHIPMENT

        if shipments_to_add > orders_to_add:
            raise RuntimeError(
                "There are not enough new orders to attach the required "
                "new shipments."
            )

        print("\n========== GENERATION PLAN ==========")
        print("New orders:", orders_to_add)
        print("New completed shipments:", shipments_to_add)
        print("New tracking events:", events_to_add)
        print("Dry run:", DRY_RUN)

        if orders_to_add == 0 and shipments_to_add == 0:
            print("Nothing to generate.")
            connection.rollback()
            return

        # Load active warehouses and SKUs.
        cursor.execute("""
            SELECT node_id, city
            FROM fulfillment_nodes
            WHERE is_active = 1
            ORDER BY node_id
        """)
        nodes = cursor.fetchall()

        cursor.execute("""
            SELECT sku_id
            FROM skus
            ORDER BY sku_id
        """)
        skus = [row[0] for row in cursor.fetchall()]

        if not nodes or not skus:
            raise RuntimeError("Active warehouses or SKUs are missing.")

        node_ids = [row[0] for row in nodes]
        node_city = {row[0]: row[1] for row in nodes}

        # Load existing inventory. Only available stock is considered.
        cursor.execute("""
            SELECT node_id, sku_id, available_quantity, reserved_quantity
            FROM inventory
        """)
        inventory_rows = cursor.fetchall()

        inventory = {}
        for node_id, sku_id, available, reserved in inventory_rows:
            inventory[(node_id, sku_id)] = {
                "available": int(available),
                "reserved": int(reserved),
            }

        total_available = sum(item["available"] for item in inventory.values())

        if shipments_to_add > total_available:
            raise RuntimeError(
                f"Need to reserve {shipments_to_add} units, but only "
                f"{total_available} units are currently available. "
                "No data has been changed."
            )

        # Load carrier/service combinations that support each destination zone.
        cursor.execute("""
            SELECT
                csz.service_zone,
                csz.carrier_id,
                csz.service_level_id,
                sl.transit_days
            FROM carrier_service_zones csz
            JOIN carriers c
                ON c.carrier_id = csz.carrier_id
            JOIN service_levels sl
                ON sl.service_level_id = csz.service_level_id
            WHERE c.is_active = 1
            ORDER BY csz.service_zone, csz.carrier_id, csz.service_level_id
        """)
        carrier_rows = cursor.fetchall()

        carrier_options = {}
        for zone, carrier_id, service_id, transit_days in carrier_rows:
            carrier_options.setdefault(zone, []).append(
                (carrier_id, service_id, int(transit_days))
            )

        # Extend carrier calendars backwards without overwriting existing rows.
        today = date.today()
        first_calendar_day = today - timedelta(days=30)
        calendar_records = []

        cursor.execute("SELECT carrier_id FROM carriers WHERE is_active = 1")
        active_carriers = [row[0] for row in cursor.fetchall()]

        for carrier_id in active_carriers:
            for offset in range(31):
                operating_date = first_calendar_day + timedelta(days=offset)
                is_operating = operating_date.weekday() != 6
                calendar_records.append((
                    carrier_id,
                    operating_date,
                    is_operating,
                    time(16, 0),
                ))

        execute_batches(cursor, """
            INSERT IGNORE INTO carrier_calendar
            (carrier_id, operating_date, is_operating, cutoff_time)
            VALUES (%s, %s, %s, %s)
        """, calendar_records)

        # Extend warehouse capacity backwards. Existing allocated_orders
        # values are not overwritten.
        capacity_records = []
        for node_id in node_ids:
            for offset in range(31):
                capacity_date = first_calendar_day + timedelta(days=offset)
                capacity_records.append((
                    node_id,
                    capacity_date,
                    100,
                    0,
                ))

        execute_batches(cursor, """
            INSERT IGNORE INTO warehouse_capacity
            (node_id, capacity_date, max_orders, allocated_orders)
            VALUES (%s, %s, %s, %s)
        """, capacity_records)

        # Read the resulting calendar and capacity data.
        cursor.execute("""
            SELECT carrier_id, operating_date, is_operating, cutoff_time
            FROM carrier_calendar
            WHERE operating_date BETWEEN %s AND %s
        """, (first_calendar_day, today))

        carrier_calendar = {
            (row[0], row[1]): (bool(row[2]), row[3])
            for row in cursor.fetchall()
        }

        cursor.execute("""
            SELECT node_id, capacity_date, max_orders, allocated_orders
            FROM warehouse_capacity
            WHERE capacity_date BETWEEN %s AND %s
        """, (first_calendar_day, today))

        capacity = {}
        for node_id, capacity_date, maximum, allocated in cursor.fetchall():
            capacity[(node_id, capacity_date)] = {
                "maximum": int(maximum),
                "allocated": int(allocated),
            }

        # Prepare dispatch options for each zone. A dispatch date must be an
        # operating day, and delivery must be no later than today.
        dispatch_options = {}

        for zone, options in carrier_options.items():
            zone_options = []

            for carrier_id, service_id, transit_days in options:
                earliest_dispatch = first_calendar_day
                latest_dispatch = today - timedelta(days=transit_days)

                dispatch_day = earliest_dispatch
                while dispatch_day <= latest_dispatch:
                    calendar_entry = carrier_calendar.get(
                        (carrier_id, dispatch_day)
                    )

                    if calendar_entry and calendar_entry[0]:
                        zone_options.append((
                            carrier_id,
                            service_id,
                            transit_days,
                            dispatch_day,
                        ))

                    dispatch_day += timedelta(days=1)

            dispatch_options[zone] = zone_options

        # Prepare unique order IDs.
        next_order_number = get_next_order_number(cursor)
        new_order_ids = [
            f"ORD-2026-{number:06d}"
            for number in range(
                next_order_number,
                next_order_number + orders_to_add
            )
        ]

        # Prepare all generated rows in memory before inserting them.
        order_records = []
        order_line_records = []
        allocation_decision_records = []
        allocation_line_specs = []
        shipment_records = []
        shipment_line_specs = []
        order_sku_by_id = {}
        promise_records = []
        tracking_records = []

        # Track stock and capacity locally; database updates happen once.
        changed_inventory = {}
        changed_capacity = {}

        shipment_counter = 1
        allocated_order_count = 0

        for order_index, order_id in enumerate(new_order_ids):
            is_to_be_shipped = order_index < shipments_to_add

            city, zone = random.choice(DESTINATIONS)
            sku_id = random.choice(skus)
            unit_price = round(random.uniform(100, 2000), 2)

            if not is_to_be_shipped:
                order_day = today - timedelta(days=random.randint(0, 30))
                order_records.append((
                    order_id,
                    f"CUST-{random.randint(1, 5000):04d}",
                    make_datetime(order_day, 10),
                    city,
                    zone,
                    "NEW",
                ))
                order_line_records.append((
                    order_id,
                    sku_id,
                    random.randint(1, 5),
                    unit_price,
                ))
                order_sku_by_id[order_id] = sku_id
                continue

            options = dispatch_options.get(zone, [])
            if not options:
                raise RuntimeError(
                    f"No operating carrier/service option found for {zone}."
                )

            # Try multiple combinations until stock and capacity are both
            # available for this SKU, warehouse and dispatch date.
            assignment = None
            shuffled_options = options[:]
            random.shuffle(shuffled_options)

            for carrier_id, service_id, transit_days, dispatch_day in shuffled_options:
                candidate_nodes = node_ids[:]
                random.shuffle(candidate_nodes)

                for node_id in candidate_nodes:
                    stock_key = (node_id, sku_id)
                    capacity_key = (node_id, dispatch_day)

                    stock_item = inventory.get(stock_key)
                    capacity_item = capacity.get(capacity_key)

                    if not stock_item or stock_item["available"] < 1:
                        continue

                    if not capacity_item:
                        continue

                    if capacity_item["allocated"] >= capacity_item["maximum"]:
                        continue

                    assignment = (
                        node_id,
                        carrier_id,
                        service_id,
                        transit_days,
                        dispatch_day,
                    )
                    break

                if assignment:
                    break

            # If the randomly selected SKU has no suitable stock, try other
            # SKUs before failing.
            if assignment is None:
                for alternative_sku in skus:
                    if alternative_sku == sku_id:
                        continue

                    for carrier_id, service_id, transit_days, dispatch_day in shuffled_options:
                        candidate_nodes = node_ids[:]
                        random.shuffle(candidate_nodes)

                        for node_id in candidate_nodes:
                            stock_key = (node_id, alternative_sku)
                            capacity_key = (node_id, dispatch_day)

                            stock_item = inventory.get(stock_key)
                            capacity_item = capacity.get(capacity_key)

                            if (
                                stock_item
                                and stock_item["available"] >= 1
                                and capacity_item
                                and capacity_item["allocated"] < capacity_item["maximum"]
                            ):
                                assignment = (
                                    node_id,
                                    carrier_id,
                                    service_id,
                                    transit_days,
                                    dispatch_day,
                                )
                                sku_id = alternative_sku
                                break

                        if assignment:
                            break

                    if assignment:
                        break

            if assignment is None:
                raise RuntimeError(
                    f"Could not find stock and capacity for generated order "
                    f"{order_id}. No data has been changed."
                )

            node_id, carrier_id, service_id, transit_days, dispatch_day = assignment
            delivery_day = dispatch_day + timedelta(days=transit_days)

            # The order must exist before its dispatch date.
            order_day = dispatch_day - timedelta(days=random.randint(1, 5))
            order_records.append((
                order_id,
                f"CUST-{random.randint(1, 5000):04d}",
                make_datetime(order_day, 10),
                city,
                zone,
                "DELIVERED",
            ))

            # One unit is allocated to each generated shipment.
            order_line_records.append((
                order_id,
                sku_id,
                1,
                unit_price,
            ))
            order_sku_by_id[order_id] = sku_id

            stock_key = (node_id, sku_id)
            inventory[stock_key]["available"] -= 1
            inventory[stock_key]["reserved"] += 1
            changed_inventory[stock_key] = (
                inventory[stock_key]["available"],
                inventory[stock_key]["reserved"],
            )

            capacity_key = (node_id, dispatch_day)
            capacity[capacity_key]["allocated"] += 1
            changed_capacity[capacity_key] = capacity[capacity_key]["allocated"]

            decision_created = make_datetime(order_day, 11)
            allocation_decision_records.append((
                order_id,
                node_id,
                "ALLOCATED",
                round(random.uniform(0.70, 1.00), 4),
                "Synthetic benchmark allocation: stock and capacity available.",
                decision_created,
            ))

            shipment_id = f"SHP-2026-BULK-{shipment_counter:06d}"
            promise_id = f"PROM-2026-BULK-{shipment_counter:06d}"

            dispatch_datetime = make_datetime(dispatch_day, 9)
            delivery_datetime = make_datetime(delivery_day, 17)

            shipment_records.append((
                shipment_id,
                order_id,
                node_id,
                carrier_id,
                service_id,
                dispatch_datetime,
                delivery_datetime,
                "DELIVERED",
            ))

            shipment_line_specs.append((shipment_id, order_id, sku_id, 1))

            promise_records.append((
                promise_id,
                order_id,
                shipment_id,
                delivery_day + timedelta(days=1),
                1,
                make_datetime(order_day, 11),
            ))

            event_times = [
                make_datetime(dispatch_day, 9),
                make_datetime(dispatch_day, 12),
                make_datetime(dispatch_day + timedelta(days=1), 9),
                make_datetime(delivery_day, 9),
                make_datetime(delivery_day, 17),
            ]

            event_types = [
                "CREATED",
                "PICKED_UP",
                "IN_TRANSIT",
                "OUT_FOR_DELIVERY",
                "DELIVERED",
            ]

            for sequence, (event_type, event_time) in enumerate(
                zip(event_types, event_times),
                start=1,
            ):
                tracking_id = (
                    f"TRK-2026-BULK-{shipment_counter:06d}-{sequence:02d}"
                )
                tracking_records.append((
                    tracking_id,
                    shipment_id,
                    sequence,
                    event_type,
                    event_time,
                    node_city.get(node_id, city),
                ))

            shipment_counter += 1
            allocated_order_count += 1

        if allocated_order_count != shipments_to_add:
            raise RuntimeError(
                f"Expected {shipments_to_add} allocated orders, "
                f"prepared {allocated_order_count}."
            )

        # Insert orders and order lines.
        execute_batches(cursor, """
            INSERT INTO orders
            (order_id, customer_id, order_date, destination_city,
             destination_zone, order_status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, order_records)

        execute_batches(cursor, """
            INSERT INTO order_lines
            (order_id, sku_id, quantity, unit_price)
            VALUES (%s, %s, %s, %s)
        """, order_line_records)

        # Retrieve the auto-generated order_line_id values in manageable
        # chunks, then map them to their order and SKU.
        order_line_id_map = {}

        for start in range(0, len(new_order_ids), BATCH_SIZE):
            id_batch = new_order_ids[start:start + BATCH_SIZE]
            placeholders = ",".join(["%s"] * len(id_batch))

            cursor.execute(
                f"""
                SELECT order_line_id, order_id, sku_id
                FROM order_lines
                WHERE order_id IN ({placeholders})
                """,
                tuple(id_batch),
            )

            for line_id, order_id, sku_id in cursor.fetchall():
                order_line_id_map[(order_id, sku_id)] = line_id

        # Insert allocation decisions and capture their auto-increment IDs.
        allocation_line_records = []
        for decision in allocation_decision_records:
            cursor.execute("""
                INSERT INTO allocation_decisions
                (order_id, node_id, decision_status, decision_score,
                 decision_reason, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, decision)

            decision_id = cursor.lastrowid
            order_id = decision[0]

            # Every generated allocated order has exactly one line.
            matching_sku = order_sku_by_id[order_id]
            line_id = order_line_id_map[(order_id, matching_sku)]

            allocation_line_records.append((
                decision_id,
                line_id,
                1,
            ))

        execute_batches(cursor, """
            INSERT INTO allocation_lines
            (decision_id, order_line_id, allocated_quantity)
            VALUES (%s, %s, %s)
        """, allocation_line_records)

        # Insert shipments and their lines.
        execute_batches(cursor, """
            INSERT INTO shipments
            (shipment_id, order_id, node_id, carrier_id, service_level_id,
             dispatch_date, actual_delivery_date, shipment_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, shipment_records)

        shipment_line_records = []
        for shipment_id, order_id, sku_id, quantity in shipment_line_specs:
            line_id = order_line_id_map[(order_id, sku_id)]
            shipment_line_records.append((
                shipment_id,
                line_id,
                quantity,
            ))

        execute_batches(cursor, """
            INSERT INTO shipment_lines
            (shipment_id, order_line_id, allocated_quantity)
            VALUES (%s, %s, %s)
        """, shipment_line_records)

        # Insert delivery promises and tracking history.
        execute_batches(cursor, """
            INSERT INTO delivery_promises
            (promise_id, order_id, shipment_id, promised_delivery_date,
             promise_version, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, promise_records)

        execute_batches(cursor, """
            INSERT INTO tracking_events
            (tracking_event_id, shipment_id, event_sequence, event_type,
             event_time, event_location)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, tracking_records)

        # Persist updated inventory and capacity counters without resetting
        # existing reserved stock or allocated capacity.
        inventory_updates = [
            (available, reserved, node_id, sku_id)
            for (node_id, sku_id), (available, reserved)
            in changed_inventory.items()
        ]

        execute_batches(cursor, """
            UPDATE inventory
            SET available_quantity = %s,
                reserved_quantity = %s
            WHERE node_id = %s AND sku_id = %s
        """, inventory_updates)

        capacity_updates = [
            (allocated, node_id, capacity_date)
            for (node_id, capacity_date), allocated
            in changed_capacity.items()
        ]

        execute_batches(cursor, """
            UPDATE warehouse_capacity
            SET allocated_orders = %s
            WHERE node_id = %s AND capacity_date = %s
        """, capacity_updates)

        if DRY_RUN:
            connection.rollback()
            print("\nDRY RUN SUCCESSFUL — no data was saved.")
            print("The transaction was rolled back intentionally.")
        else:
            connection.commit()
            print("\nDATA GENERATION SUCCESSFUL.")

        print("\n========== PREPARED RECORDS ==========")
        print("Orders:", len(order_records))
        print("Order lines:", len(order_line_records))
        print("Allocation decisions:", len(allocation_decision_records))
        print("Allocation lines:", len(allocation_line_records))
        print("Shipments:", len(shipment_records))
        print("Shipment lines:", len(shipment_line_records))
        print("Delivery promises:", len(promise_records))
        print("Tracking events:", len(tracking_records))
        print("Inventory rows updated:", len(changed_inventory))
        print("Capacity rows updated:", len(changed_capacity))

        if DRY_RUN:
            print("\nNext step: change DRY_RUN = False and run again.")
        else:
            print("\nVerify final counts in MySQL Workbench.")

    except Exception as error:
        connection.rollback()
        print("\nGENERATION FAILED. All changes in this run were rolled back.")
        print("Error:", error)

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()

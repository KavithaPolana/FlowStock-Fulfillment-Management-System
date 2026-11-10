
USE fulfillment_db;

-- 1. SKU master
CREATE TABLE skus (
    sku_id VARCHAR(30) PRIMARY KEY,
    sku_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    unit_weight DECIMAL(10,2) NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Fulfillment nodes (warehouses)
CREATE TABLE fulfillment_nodes (
    node_id VARCHAR(30) PRIMARY KEY,
    node_name VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    service_zone VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- 3. Carrier master
CREATE TABLE carriers (
    carrier_id VARCHAR(30) PRIMARY KEY,
    carrier_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE
);

-- 4. Service levels
CREATE TABLE service_levels (
    service_level_id VARCHAR(30) PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL,
    transit_days INT NOT NULL,
    UNIQUE(service_name)
);

-- 5. Orders
CREATE TABLE orders (
    order_id VARCHAR(30) PRIMARY KEY,
    customer_id VARCHAR(30) NOT NULL,
    order_date DATETIME NOT NULL,
    destination_city VARCHAR(100) NOT NULL,
    destination_zone VARCHAR(50) NOT NULL,
    order_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6. Order lines
CREATE TABLE order_lines (
    order_line_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(30) NOT NULL,
    sku_id VARCHAR(30) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
    CHECK (quantity > 0),
    CHECK (unit_price >= 0),
    UNIQUE(order_id, sku_id)
);

-- 7. Inventory
CREATE TABLE inventory (
    inventory_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    node_id VARCHAR(30) NOT NULL,
    sku_id VARCHAR(30) NOT NULL,
    available_quantity INT NOT NULL DEFAULT 0,
    reserved_quantity INT NOT NULL DEFAULT 0,
    FOREIGN KEY (node_id) REFERENCES fulfillment_nodes(node_id),
    FOREIGN KEY (sku_id) REFERENCES skus(sku_id),
    CHECK (available_quantity >= 0),
    CHECK (reserved_quantity >= 0),
    UNIQUE(node_id, sku_id)
);

-- 8. Warehouse capacity
CREATE TABLE warehouse_capacity (
    capacity_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    node_id VARCHAR(30) NOT NULL,
    capacity_date DATE NOT NULL,
    max_orders INT NOT NULL,
    allocated_orders INT NOT NULL DEFAULT 0,
    FOREIGN KEY (node_id) REFERENCES fulfillment_nodes(node_id),
    CHECK (max_orders >= 0),
    CHECK (allocated_orders >= 0),
    CHECK (allocated_orders <= max_orders),
    UNIQUE(node_id, capacity_date)
);

-- 9. Carrier service zones
CREATE TABLE carrier_service_zones (
    zone_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    carrier_id VARCHAR(30) NOT NULL,
    service_level_id VARCHAR(30) NOT NULL,
    service_zone VARCHAR(50) NOT NULL,
    FOREIGN KEY (carrier_id) REFERENCES carriers(carrier_id),
    FOREIGN KEY (service_level_id)
        REFERENCES service_levels(service_level_id),
    UNIQUE(carrier_id, service_level_id, service_zone)
);

-- 10. Carrier calendar and cutoff
CREATE TABLE carrier_calendar (
    calendar_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    carrier_id VARCHAR(30) NOT NULL,
    operating_date DATE NOT NULL,
    is_operating BOOLEAN NOT NULL DEFAULT TRUE,
    cutoff_time TIME NOT NULL,
    FOREIGN KEY (carrier_id) REFERENCES carriers(carrier_id),
    UNIQUE(carrier_id, operating_date)
);

-- 11. Shipments
CREATE TABLE shipments (
    shipment_id VARCHAR(40) PRIMARY KEY,
    order_id VARCHAR(30) NOT NULL,
    node_id VARCHAR(30) NOT NULL,
    carrier_id VARCHAR(30),
    service_level_id VARCHAR(30),
    dispatch_date DATETIME,
    actual_delivery_date DATETIME,
    shipment_status VARCHAR(30) NOT NULL DEFAULT 'CREATED',
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (node_id) REFERENCES fulfillment_nodes(node_id),
    FOREIGN KEY (carrier_id) REFERENCES carriers(carrier_id),
    FOREIGN KEY (service_level_id)
        REFERENCES service_levels(service_level_id)
);

-- Bridge table: shipments and order lines
CREATE TABLE shipment_lines (
    shipment_line_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    shipment_id VARCHAR(40) NOT NULL,
    order_line_id BIGINT NOT NULL,
    allocated_quantity INT NOT NULL,
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    FOREIGN KEY (order_line_id) REFERENCES order_lines(order_line_id),
    CHECK (allocated_quantity > 0)
);

-- 12. Tracking events
CREATE TABLE tracking_events (
    tracking_event_id VARCHAR(80) PRIMARY KEY,
    shipment_id VARCHAR(40) NOT NULL,
    event_sequence INT NOT NULL,
    event_type VARCHAR(40) NOT NULL,
    event_time DATETIME NOT NULL,
    event_location VARCHAR(100),
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    UNIQUE(shipment_id, event_sequence)
);

-- 13. Delivery promises
CREATE TABLE delivery_promises (
    promise_id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(30) NOT NULL,
    shipment_id VARCHAR(40),
    promised_delivery_date DATE NOT NULL,
    promise_version INT NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    UNIQUE(order_id, promise_version, shipment_id)
);

-- 14. Allocation decision history
CREATE TABLE allocation_decisions (
    decision_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(30) NOT NULL,
    node_id VARCHAR(30) NOT NULL,
    decision_status VARCHAR(30) NOT NULL,
    decision_score DECIMAL(10,4),
    decision_reason VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (node_id) REFERENCES fulfillment_nodes(node_id)
);

-- 15. Exception records
CREATE TABLE exceptions (
    exception_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(30),
    shipment_id VARCHAR(40),
    issue_type VARCHAR(80) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    description VARCHAR(500),
    detected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id)
);

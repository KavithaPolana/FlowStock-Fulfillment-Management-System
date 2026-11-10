
import { useEffect, useMemo, useState } from "react";
import {
  Warehouse,
  Package,
  Boxes,
  Search,
  RefreshCw,
  MapPin,
  Activity,
  AlertTriangle
} from "lucide-react";

import { getWarehouses, getInventory } from "../services/api";

const LOW_STOCK_LIMIT = 100;

function Warehouses() {
  const [warehouses, setWarehouses] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = async () => {
    try {
      setLoading(true);
      setError("");

      const [warehouseResponse, inventoryResponse] =
        await Promise.all([getWarehouses(), getInventory()]);

      const warehouseData = warehouseResponse.data;
      const inventoryData = inventoryResponse.data;

      setWarehouses(
        Array.isArray(warehouseData)
          ? warehouseData
          : warehouseData.warehouses || []
      );

      setInventory(
        Array.isArray(inventoryData)
          ? inventoryData
          : inventoryData.inventory || []
      );
    } catch (err) {
      console.error("Warehouse loading error:", err);
      setError("Unable to load warehouse and inventory data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalAvailable = inventory.reduce(
    (sum, item) => sum + Number(item.available_quantity || 0),
    0
  );

  const totalReserved = inventory.reduce(
    (sum, item) => sum + Number(item.reserved_quantity || 0),
    0
  );

  const activeWarehouses = warehouses.filter(
    (warehouse) =>
      warehouse.is_active === 1 ||
      warehouse.is_active === true
  ).length;

  const lowStockItems = inventory.filter(
    (item) =>
      Number(item.available_quantity || 0) <= LOW_STOCK_LIMIT
  );

  const filteredInventory = useMemo(() => {
    const term = search.toLowerCase();

    return inventory.filter((item) =>
      [
        item.node_id,
        item.node_name,
        item.city,
        item.sku_id,
        item.sku_name,
        item.category
      ]
        .filter(Boolean)
        .some((value) =>
          String(value).toLowerCase().includes(term)
        )
    );
  }, [inventory, search]);

  if (loading) {
    return <div className="page-container">Loading warehouse data...</div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Warehouses & Inventory</h1>
          <p>Monitor warehouse locations and available stock.</p>
        </div>

        <button className="primary-btn" onClick={loadData}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {error && <p className="error-message">{error}</p>}

      {/* Summary Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon"><Warehouse /></div>
          <div>
            <p>Total Warehouses</p>
            <h2>{warehouses.length}</h2>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon"><Activity /></div>
          <div>
            <p>Active Warehouses</p>
            <h2>{activeWarehouses}</h2>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon"><Package /></div>
          <div>
            <p>Available Stock</p>
            <h2>{totalAvailable.toLocaleString()}</h2>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon"><Boxes /></div>
          <div>
            <p>Reserved Stock</p>
            <h2>{totalReserved.toLocaleString()}</h2>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <AlertTriangle color="#dc2626" />
          </div>
          <div>
            <p>Low Stock Records</p>
            <h2 style={{ color: "#dc2626" }}>
              {lowStockItems.length}
            </h2>
          </div>
        </div>
      </div>

      {/* Low Stock Alert */}
      {lowStockItems.length > 0 && (
        <section
          className="content-card"
          style={{
            borderLeft: "4px solid #dc2626",
            marginBottom: "20px"
          }}
        >
          <h2 style={{ color: "#dc2626" }}>
            <AlertTriangle size={20} /> Low Stock Alert
          </h2>

          <p>
            {lowStockItems.length} inventory records have
            { " " }{LOW_STOCK_LIMIT} or fewer available units.
            Please review these items before allocating new orders.
          </p>
        </section>
      )}

      {/* Warehouse Locations */}
      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>Warehouse Locations</h2>
            <p>Registered fulfillment centers</p>
          </div>
        </div>

        <div className="warehouse-grid">
          {warehouses.map((warehouse) => (
            <div className="warehouse-card" key={warehouse.node_id}>
              <div className="warehouse-card-top">
                <Warehouse size={22} />
                <span
                  className={
                    warehouse.is_active
                      ? "status-badge active"
                      : "status-badge"
                  }
                >
                  {warehouse.is_active ? "Active" : "Inactive"}
                </span>
              </div>

              <h3>{warehouse.node_name}</h3>

              <p>
                <MapPin size={14} />
                {warehouse.city}, {warehouse.state}
              </p>

              <small>
                ID: {warehouse.node_id} | Zone: {warehouse.service_zone}
              </small>
            </div>
          ))}
        </div>

        {warehouses.length === 0 && (
          <p className="empty-message">No warehouses found.</p>
        )}
      </section>

      {/* Inventory Details */}
      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>Inventory Details</h2>
            <p>Stock availability across warehouses</p>
          </div>

          <div className="search-box">
            <Search size={17} />
            <input
              type="text"
              placeholder="Search warehouse or SKU..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Warehouse ID</th>
                <th>Warehouse</th>
                <th>SKU ID</th>
                <th>SKU Name</th>
                <th>Available</th>
                <th>Reserved</th>
                <th>Total Stock</th>
                <th>Stock Status</th>
              </tr>
            </thead>

            <tbody>
              {filteredInventory.map((item, index) => {
                const available = Number(item.available_quantity || 0);
                const reserved = Number(item.reserved_quantity || 0);
                const isLowStock = available <= LOW_STOCK_LIMIT;

                return (
                  <tr
                    key={
                      item.inventory_id ||
                      `${item.node_id}-${item.sku_id}-${index}`
                    }
                  >
                    <td>{item.node_id}</td>
                    <td>{item.node_name || item.city || "—"}</td>
                    <td>{item.sku_id}</td>
                    <td>{item.sku_name || "—"}</td>
                    <td
                      style={{
                        color: isLowStock ? "#dc2626" : "inherit",
                        fontWeight: isLowStock ? "bold" : "normal"
                      }}
                    >
                      {available}
                    </td>
                    <td>{reserved}</td>
                    <td>{available + reserved}</td>
                    <td>
                      <span
                        style={{
                          color: isLowStock ? "#dc2626" : "#15803d",
                          background: isLowStock ? "#fee2e2" : "#dcfce7",
                          padding: "5px 10px",
                          borderRadius: "12px",
                          fontSize: "12px",
                          fontWeight: "600"
                        }}
                      >
                        {isLowStock ? "Low Stock" : "Available"}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filteredInventory.length === 0 && (
          <p className="empty-message">No inventory records found.</p>
        )}

        <p className="table-footer">
          Showing {filteredInventory.length} of {inventory.length} inventory records
        </p>
      </section>
    </div>
  );
}

export default Warehouses;

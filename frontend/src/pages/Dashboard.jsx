
import { useEffect, useState } from "react";
import {
  ShoppingCart,
  Warehouse,
  Truck,
  AlertTriangle,
  RefreshCw,
  PackageCheck,
  Clock3,
  Activity,
} from "lucide-react";

import { getDashboard, getOrders, getShipments, getExceptions } from "../services/api";

function Dashboard() {
  const [stats, setStats] = useState({
    total_orders: 0,
    total_nodes: 0,
    total_shipments: 0,
    total_exceptions: 0,
  });

  const [orders, setOrders] = useState([]);
  const [shipments, setShipments] = useState([]);
  const [exceptions, setExceptions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = async () => {
    try {
      setLoading(true);
      setError("");

      const [dashboardRes, ordersRes, shipmentsRes, exceptionsRes] =
        await Promise.all([
          getDashboard(),
          getOrders(),
          getShipments(),
          getExceptions(),
        ]);

      setStats(dashboardRes.data);
      setOrders(ordersRes.data.orders || []);
      setShipments(shipmentsRes.data.shipments || []);
      setExceptions(exceptionsRes.data.exceptions || []);
    } catch (err) {
      console.error("Dashboard loading error:", err);
      setError("Unable to load dashboard data. Please check your backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const statCards = [
    {
      title: "Total Orders",
      value: stats.total_orders,
      icon: ShoppingCart,
      color: "green",
      description: "Orders in the system",
    },
    {
      title: "Fulfillment Nodes",
      value: stats.total_nodes,
      icon: Warehouse,
      color: "blue",
      description: "Available warehouse nodes",
    },
    {
      title: "Total Shipments",
      value: stats.total_shipments,
      icon: Truck,
      color: "purple",
      description: "Created shipments",
    },
    {
      title: "Exceptions",
      value: stats.total_exceptions,
      icon: AlertTriangle,
      color: "orange",
      description: "Recorded exception events",
    },
  ];

  const statusColor = (status) => {
    const colors = {
      NEW: "status-new",
      PENDING: "status-new",
      ALLOCATED: "status-allocated",
      CREATED: "status-allocated",
      PICKED_UP: "status-transit",
      IN_TRANSIT: "status-transit",
      OUT_FOR_DELIVERY: "status-transit",
      DELIVERED: "status-delivered",
    };

    return colors[status] || "status-default";
  };

  if (loading) {
    return (
      <div className="loading-state">
        <RefreshCw className="spin" size={28} />
        <p>Loading your fulfillment dashboard...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-content">
      <div className="dashboard-welcome">
        <div>
          <h2>Overview</h2>
          <p>Monitor your orders, warehouses and delivery operations.</p>
        </div>

        <button className="refresh-button" onClick={loadDashboard}>
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="stats-grid">
        {statCards.map((card) => {
          const Icon = card.icon;

          return (
            <div className="stat-card" key={card.title}>
              <div className="stat-card-top">
                <div className={`stat-icon ${card.color}`}>
                  <Icon size={22} />
                </div>
                <Activity size={18} className="stat-decoration" />
              </div>

              <h3>{card.value}</h3>
              <h4>{card.title}</h4>
              <p>{card.description}</p>
            </div>
          );
        })}
      </div>

      <div className="dashboard-grid">
        <section className="content-card">
          <div className="section-heading">
            <div>
              <h3>Recent Orders</h3>
              <p>Latest customer orders</p>
            </div>
            <ShoppingCart size={20} />
          </div>

          {orders.length === 0 ? (
            <p className="empty-state">No orders available.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>Destination</th>
                    <th>Units</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.slice(0, 6).map((order) => (
                    <tr key={order.order_id}>
                      <td className="table-id">{order.order_id}</td>
                      <td>{order.destination_city}</td>
                      <td>{order.total_units}</td>
                      <td>
                        <span className={`status-badge ${statusColor(order.order_status)}`}>
                          {order.order_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="content-card">
          <div className="section-heading">
            <div>
              <h3>Shipment Overview</h3>
              <p>Current shipment status</p>
            </div>
            <Truck size={20} />
          </div>

          <div className="shipment-summary">
            <div className="shipment-summary-item">
              <div className="summary-icon delivered">
                <PackageCheck size={19} />
              </div>
              <div>
                <strong>
                  {shipments.filter((s) => s.shipment_status === "DELIVERED").length}
                </strong>
                <span>Delivered</span>
              </div>
            </div>

            <div className="shipment-summary-item">
              <div className="summary-icon transit">
                <Truck size={19} />
              </div>
              <div>
                <strong>
                  {shipments.filter((s) =>
                    ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY"].includes(s.shipment_status)
                  ).length}
                </strong>
                <span>In Transit</span>
              </div>
            </div>

            <div className="shipment-summary-item">
              <div className="summary-icon pending">
                <Clock3 size={19} />
              </div>
              <div>
                <strong>
                  {shipments.filter((s) => !["DELIVERED", "CANCELLED"].includes(s.shipment_status)).length}
                </strong>
                <span>Pending / Active</span>
              </div>
            </div>
          </div>

          <div className="shipment-list">
            {shipments.slice(0, 4).map((shipment) => (
              <div className="shipment-row" key={shipment.shipment_id}>
                <div>
                  <strong>{shipment.shipment_id}</strong>
                  <span>{shipment.destination_city}</span>
                </div>
                <span className={`status-badge ${statusColor(shipment.shipment_status)}`}>
                  {shipment.shipment_status}
                </span>
              </div>
            ))}

            {shipments.length === 0 && (
              <p className="empty-state">No shipments created yet.</p>
            )}
          </div>
        </section>
      </div>

      <section className="content-card exceptions-card">
        <div className="section-heading">
          <div>
            <h3>Recent Exceptions</h3>
            <p>Issues detected by the fulfillment system</p>
          </div>
          <AlertTriangle size={20} />
        </div>

        {exceptions.length === 0 ? (
          <p className="empty-state">No exceptions recorded.</p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Exception Type</th>
                  <th>Order ID</th>
                  <th>Severity</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {exceptions.slice(0, 5).map((exception) => (
                  <tr key={exception.exception_id}>
                    <td className="table-id">{exception.issue_type}</td>
                    <td>{exception.order_id || "—"}</td>
                    <td>
                      <span className="severity-badge">
                        {exception.severity}
                      </span>
                    </td>
                    <td className="description-cell">
                      {exception.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

export default Dashboard;

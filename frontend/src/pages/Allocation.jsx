
import { useEffect, useState } from "react";
import {
  Search,
  RefreshCw,
  GitBranch,
  MapPin,
  Boxes,
  CheckCircle,
  AlertCircle,
  LoaderCircle,
} from "lucide-react";

import { getOrders, allocateOrder } from "../services/api";

function Allocation() {
  const [orders, setOrders] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [allocatingId, setAllocatingId] = useState(null);
  const [message, setMessage] = useState(null);

  const loadOrders = async () => {
    try {
      setLoading(true);
      const response = await getOrders();
      setOrders(response.data.orders || []);
    } catch (error) {
      console.error("Allocation orders error:", error);
      setMessage({
        type: "error",
        text: "Unable to load orders. Please check the backend.",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, []);

  const pendingOrders = orders.filter(
    (order) => order.order_status === "NEW"
  );

  const filteredOrders = pendingOrders.filter((order) =>
    order.order_id?.toLowerCase().includes(search.toLowerCase()) ||
    order.destination_city?.toLowerCase().includes(search.toLowerCase())
  );

  const handleAllocation = async (orderId) => {
    const confirmed = window.confirm(
      `Are you sure you want to allocate ${orderId}? This will reserve warehouse inventory.`
    );

    if (!confirmed) return;

    try {
      setAllocatingId(orderId);
      setMessage(null);

      const response = await allocateOrder(orderId);

      setMessage({
        type: "success",
        text:
          response.data.message ||
          `Allocation completed for ${orderId}.`,
      });

      await loadOrders();
    } catch (error) {
      console.error("Allocation error:", error);

      setMessage({
        type: "error",
        text:
          error.response?.data?.message ||
          error.response?.data?.error ||
          "Allocation failed. Check stock availability and backend logs.",
      });
    } finally {
      setAllocatingId(null);
    }
  };

  return (
    <div className="allocation-page">

      <div className="page-toolbar">
        <div>
          <h2>Order Allocation</h2>
          <p>
            Assign customer orders to suitable fulfillment warehouses.
          </p>
        </div>

        <button className="refresh-button" onClick={loadOrders}>
          <RefreshCw size={17} />
          Refresh
        </button>
      </div>

      <div className="orders-summary">
        <div className="orders-summary-card">
          <GitBranch size={22} />
          <div>
            <strong>{orders.length}</strong>
            <span>Total Orders</span>
          </div>
        </div>

        <div className="orders-summary-card">
          <Boxes size={22} />
          <div>
            <strong>{pendingOrders.length}</strong>
            <span>Waiting for Allocation</span>
          </div>
        </div>

        <div className="orders-summary-card">
          <CheckCircle size={22} />
          <div>
            <strong>
              {orders.filter(o => o.order_status === "ALLOCATED").length}
            </strong>
            <span>Allocated Orders</span>
          </div>
        </div>
      </div>

      {message && (
        <div className={`allocation-message ${message.type}`}>
          {message.type === "success" ? (
            <CheckCircle size={19} />
          ) : (
            <AlertCircle size={19} />
          )}
          <span>{message.text}</span>
        </div>
      )}

      <div className="orders-table-card">

        <div className="orders-filters">
          <div className="search-box">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search order ID or destination..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="table-heading">
          <div>
            <h3>Orders Waiting for Allocation</h3>
            <p>Select an order to start warehouse allocation.</p>
          </div>
          <span>{filteredOrders.length} orders found</span>
        </div>

        {loading ? (
          <p className="orders-message">Loading orders...</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Destination</th>
                  <th>Order Date</th>
                  <th>Total Units</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {filteredOrders.map((order) => (
                  <tr key={order.order_id}>
                    <td className="order-id-cell">
                      {order.order_id}
                    </td>

                    <td>
                      <span className="destination-cell">
                        <MapPin size={14} />
                        {order.destination_city}
                      </span>
                    </td>

                    <td>
                      {String(order.order_date || "").slice(0, 16)}
                    </td>

                    <td>{order.total_units}</td>

                    <td>
                      <span className="status-badge status-new">
                        NEW
                      </span>
                    </td>

                    <td>
                      <button
                        className="view-button"
                        disabled={allocatingId === order.order_id}
                        onClick={() => handleAllocation(order.order_id)}
                      >
                        {allocatingId === order.order_id ? (
                          <>
                            <LoaderCircle size={16} />
                            Allocating...
                          </>
                        ) : (
                          <>
                            <GitBranch size={16} />
                            Allocate Order
                          </>
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredOrders.length === 0 && !loading && (
              <p className="orders-message">
                No NEW orders found for this search.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Allocation;

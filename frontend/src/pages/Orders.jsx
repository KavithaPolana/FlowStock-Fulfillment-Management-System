
import { useEffect, useState } from "react";
import { Search, RefreshCw, Eye, MapPin, X } from "lucide-react";
import { getOrders, getOrderDetails } from "../services/api";

function Orders() {
  const [orders, setOrders] = useState([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [detailsLoading, setDetailsLoading] = useState(false);

  const loadOrders = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await getOrders();
      setOrders(response.data.orders || []);
    } catch (err) {
      console.error(err);
      setError("Unable to load orders. Check your backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadOrders();
  }, []);

  const viewOrder = async (orderId) => {
    try {
      setDetailsLoading(true);
      const response = await getOrderDetails(orderId);
      setSelectedOrder(response.data);
    } catch (err) {
      console.error(err);
      alert("Unable to load order details.");
    } finally {
      setDetailsLoading(false);
    }
  };

  const filteredOrders = orders.filter((order) => {
    const matchesSearch =
      order.order_id?.toLowerCase().includes(search.toLowerCase()) ||
      order.destination_city?.toLowerCase().includes(search.toLowerCase());

    const matchesStatus =
      status === "ALL" || order.order_status === status;

    return matchesSearch && matchesStatus;
  });

  const getStatusClass = (value) => {
    if (value === "DELIVERED") return "status-delivered";
    if (value === "ALLOCATED") return "status-allocated";
    if (value === "IN_TRANSIT") return "status-transit";
    return "status-new";
  };

  return (
    <div className="orders-page">
      <div className="page-toolbar">
        <div>
          <h2>All Orders</h2>
          <p>Manage and monitor customer orders.</p>
        </div>
        <button className="refresh-button" onClick={loadOrders}>
          <RefreshCw size={17} /> Refresh
        </button>
      </div>

      <div className="orders-summary">
        {[
          ["Total Orders", orders.length],
          ["New Orders", orders.filter(o => o.order_status === "NEW").length],
          ["Allocated", orders.filter(o => o.order_status === "ALLOCATED").length],
          ["Delivered", orders.filter(o => o.order_status === "DELIVERED").length],
        ].map(([label, count]) => (
          <div className="orders-summary-card" key={label}>
            <div>
              <strong>{count}</strong>
              <span>{label}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="orders-table-card">
        <div className="orders-filters">
          <div className="search-box">
            <Search size={18} />
            <input
              placeholder="Search order ID or destination..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="ALL">All Statuses</option>
            <option value="NEW">New</option>
            <option value="ALLOCATED">Allocated</option>
            <option value="IN_TRANSIT">In Transit</option>
            <option value="DELIVERED">Delivered</option>
          </select>
        </div>

        {loading ? (
          <p className="orders-message">Loading orders...</p>
        ) : error ? (
          <p className="orders-error">{error}</p>
        ) : (
          <>
            <div className="table-heading">
              <h3>Order Records</h3>
              <span>{filteredOrders.length} orders found</span>
            </div>

            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>Customer ID</th>
                    <th>Destination</th>
                    <th>Order Date</th>
                    <th>Units</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map((order) => (
                    <tr key={order.order_id}>
                      <td className="order-id-cell">{order.order_id}</td>
                      <td>{order.customer_id}</td>
                      <td>
                        <span className="destination-cell">
                          <MapPin size={14} />
                          {order.destination_city}
                        </span>
                      </td>
                      <td>{String(order.order_date || "").slice(0, 10)}</td>
                      <td>{order.total_units}</td>
                      <td>
                        <span className={`status-badge ${getStatusClass(order.order_status)}`}>
                          {order.order_status}
                        </span>
                      </td>
                      <td>
                        <button className="view-button" onClick={() => viewOrder(order.order_id)}>
                          <Eye size={16} /> View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {filteredOrders.length === 0 && (
              <p className="orders-message">No matching orders found.</p>
            )}
          </>
        )}
      </div>

      {detailsLoading && (
        <div className="modal-overlay">
          <div className="order-modal">Loading order details...</div>
        </div>
      )}

      {selectedOrder && (
        <div className="modal-overlay">
          <div className="order-modal">
            <div className="modal-header">
              <div>
                <h2>Order Details</h2>
                <p>{selectedOrder.order?.order_id}</p>
              </div>
              <button className="modal-close" onClick={() => setSelectedOrder(null)}>
                <X size={21} />
              </button>
            </div>

            <div className="order-detail-grid">
              <div>
                <span>Destination</span>
                <strong>{selectedOrder.order?.destination_city}</strong>
              </div>
              <div>
                <span>Status</span>
                <strong>{selectedOrder.order?.order_status}</strong>
              </div>
              <div>
                <span>Customer ID</span>
                <strong>{selectedOrder.order?.customer_id}</strong>
              </div>
              <div>
                <span>Order Date</span>
                <strong>{String(selectedOrder.order?.order_date || "").slice(0, 10)}</strong>
              </div>
            </div>

            <h3 className="modal-section-title">Order Items</h3>
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>SKU</th>
                    <th>Product</th>
                    <th>Quantity</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedOrder.lines || []).map((line) => (
                    <tr key={line.order_line_id}>
                      <td>{line.sku_id}</td>
                      <td>{line.sku_name}</td>
                      <td>{line.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <button className="modal-done-button" onClick={() => setSelectedOrder(null)}>
              Close Details
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default Orders;

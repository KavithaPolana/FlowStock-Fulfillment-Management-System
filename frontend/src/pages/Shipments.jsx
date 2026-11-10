
import { useEffect, useState } from "react";
import {
  RefreshCw,
  Truck,
  Package,
  Plus,
  Eye,
  X,
  Clock,
  CheckCircle,
} from "lucide-react";

import {
  getShipments,
  getOrders,
  createShipment,
  getShipmentTracking,
  addTrackingEvent,
} from "../services/api";

const trackingStages = [
  "CREATED",
  "PICKED_UP",
  "IN_TRANSIT",
  "OUT_FOR_DELIVERY",
  "DELIVERED",
];

function getLocalDateTime() {
  const date = new Date();
  const offset = date.getTimezoneOffset();

  return new Date(date.getTime() - offset * 60000)
    .toISOString()
    .slice(0, 16);
}

// Find the next valid tracking event
function getNextTrackingStage(data) {
  const events = data?.tracking_events || data?.events || [];

  if (events.length === 0) {
    return "CREATED";
  }

  const latestEvent = events[events.length - 1].event_type;
  const currentIndex = trackingStages.indexOf(latestEvent);

  if (currentIndex === -1) {
    return "";
  }

  return trackingStages[currentIndex + 1] || "";
}

function Shipments() {
  const [shipments, setShipments] = useState([]);
  const [orders, setOrders] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState("");

  const [tracking, setTracking] = useState(null);
  const [selectedShipmentId, setSelectedShipmentId] = useState("");

  const [eventType, setEventType] = useState("");
  const [eventTime, setEventTime] = useState(getLocalDateTime());
  const [eventLocation, setEventLocation] = useState("");

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [savingEvent, setSavingEvent] = useState(false);

  const [message, setMessage] = useState(null);

  // Load shipments and orders
  const loadData = async () => {
    try {
      setLoading(true);

      const [shipmentResponse, orderResponse] = await Promise.all([
        getShipments(),
        getOrders(),
      ]);

      setShipments(shipmentResponse.data.shipments || []);
      setOrders(orderResponse.data.orders || []);
    } catch (error) {
      console.error("Loading error:", error);

      setMessage({
        type: "error",
        text: "Unable to load shipment data.",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const allocatedOrders = orders.filter(
    (order) => order.order_status === "ALLOCATED"
  );

  // Create shipment
  const handleCreateShipment = async () => {
    if (!selectedOrder) return;

    if (!window.confirm(`Create shipments for ${selectedOrder}?`)) {
      return;
    }

    try {
      setCreating(true);
      setMessage(null);

      const response = await createShipment(selectedOrder);

      setMessage({
        type: "success",
        text: response.data.message || "Shipment created successfully.",
      });

      setSelectedOrder("");

      await loadData();
    } catch (error) {
      console.error("Shipment creation error:", error);

      setMessage({
        type: "error",
        text:
          error.response?.data?.message ||
          error.response?.data?.error ||
          "Shipment creation failed.",
      });
    } finally {
      setCreating(false);
    }
  };

  // View shipment tracking
  const viewTracking = async (shipmentId) => {
    try {
      setSelectedShipmentId(shipmentId);
      setTracking(null);
      setMessage(null);

      const response = await getShipmentTracking(shipmentId);

      setTracking(response.data);

      // Automatically select the next valid event
      setEventType(getNextTrackingStage(response.data));

      setEventTime(getLocalDateTime());
      setEventLocation("");
    } catch (error) {
      console.error("Tracking fetch error:", error);

      setMessage({
        type: "error",
        text: "Unable to load tracking details.",
      });
    }
  };

  const events =
    tracking?.tracking_events ||
    tracking?.events ||
    [];

  const latestEvent = events.length
    ? events[events.length - 1].event_type
    : "";

  const nextStageIndex = trackingStages.indexOf(latestEvent);

  const nextStages = events.length === 0
    ? ["CREATED"]
    : trackingStages.slice(nextStageIndex + 1);

  // Add tracking event
  const handleAddEvent = async (e) => {
    e.preventDefault();

    if (!selectedShipmentId) {
      alert("Please select a shipment.");
      return;
    }

    if (!eventType) {
      alert("No valid next tracking event is available.");
      return;
    }

    if (!eventLocation.trim()) {
      alert("Please enter the tracking location.");
      return;
    }

    if (!eventTime) {
      alert("Please select the event time.");
      return;
    }

    const trackingData = {
      shipment_id: selectedShipmentId,
      event_type: eventType,
      event_time: eventTime,
      location: eventLocation.trim(),
    };

    console.log("Sending tracking data:", trackingData);

    try {
      setSavingEvent(true);
      setMessage(null);

      const response = await addTrackingEvent(trackingData);

      // Reload tracking history after successful save
      const trackingResponse = await getShipmentTracking(
        selectedShipmentId
      );

      setTracking(trackingResponse.data);

      // Select the next event automatically
      setEventType(getNextTrackingStage(trackingResponse.data));

      setEventLocation("");
      setEventTime(getLocalDateTime());

      await loadData();

      setMessage({
        type: "success",
        text:
          response.data.message ||
          `${trackingData.event_type} event added successfully.`,
      });
    } catch (error) {
      console.error("TRACKING ERROR:", error.response?.data || error);

      const errorMessage =
        error.response?.data?.message ||
        error.response?.data?.error ||
        JSON.stringify(error.response?.data) ||
        error.message ||
        "Unknown tracking error.";

      alert("Tracking Error: " + errorMessage);

      setMessage({
        type: "error",
        text: errorMessage,
      });
    } finally {
      setSavingEvent(false);
    }
  };

  // Shipment status styling
  const statusClass = (status) => {
    if (status === "DELIVERED") return "status-delivered";
    if (status === "IN_TRANSIT") return "status-transit";
    if (status === "OUT_FOR_DELIVERY") return "status-allocated";

    return "status-new";
  };

  return (
    <div className="shipments-page">

      {/* Page heading */}
      <div className="page-toolbar">
        <div>
          <h2>Shipment Management</h2>
          <p>Create shipments and monitor delivery progress.</p>
        </div>

        <button className="refresh-button" onClick={loadData}>
          <RefreshCw size={17} />
          Refresh
        </button>
      </div>

      {/* Shipment summary */}
      <div className="orders-summary">

        <div className="orders-summary-card">
          <Truck size={22} />
          <div>
            <strong>{shipments.length}</strong>
            <span>Total Shipments</span>
          </div>
        </div>

        <div className="orders-summary-card">
          <Package size={22} />
          <div>
            <strong>
              {
                shipments.filter(
                  (s) => s.shipment_status === "CREATED"
                ).length
              }
            </strong>
            <span>Created</span>
          </div>
        </div>

        <div className="orders-summary-card">
          <CheckCircle size={22} />
          <div>
            <strong>
              {
                shipments.filter(
                  (s) => s.shipment_status === "DELIVERED"
                ).length
              }
            </strong>
            <span>Delivered</span>
          </div>
        </div>

      </div>

      {/* Messages */}
      {message && (
        <div className={`allocation-message ${message.type}`}>
          {message.text}
        </div>
      )}

      {/* Create shipment */}
      <div className="orders-table-card shipment-create-card">

        <div className="table-heading">
          <div>
            <h3>Create New Shipment</h3>
            <p>
              Choose an allocated order to generate its shipment records.
            </p>
          </div>
        </div>

        <div className="shipment-create-controls">

          <select
            value={selectedOrder}
            onChange={(e) => setSelectedOrder(e.target.value)}
          >
            <option value="">Select an allocated order</option>

            {allocatedOrders.map((order) => (
              <option
                key={order.order_id}
                value={order.order_id}
              >
                {order.order_id} — {order.destination_city}
              </option>
            ))}
          </select>

          <button
            className="view-button"
            onClick={handleCreateShipment}
            disabled={creating || !selectedOrder}
          >
            <Plus size={17} />
            {creating ? "Creating..." : "Create Shipment"}
          </button>

        </div>
      </div>

      {/* All shipments */}
      <div className="orders-table-card">

        <div className="table-heading">
          <h3>All Shipments</h3>
          <span>{shipments.length} shipments found</span>
        </div>

        {loading ? (
          <p className="orders-message">Loading shipments...</p>
        ) : (
          <div className="table-scroll">

            <table className="data-table">

              <thead>
                <tr>
                  <th>Shipment ID</th>
                  <th>Order ID</th>
                  <th>Warehouse</th>
                  <th>Carrier</th>
                  <th>Destination</th>
                  <th>Delivery Date</th>
                  <th>Status</th>
                  <th>Tracking</th>
                </tr>
              </thead>

              <tbody>
                {shipments.map((shipment) => (
                  <tr key={shipment.shipment_id}>

                    <td className="order-id-cell">
                      {shipment.shipment_id}
                    </td>

                    <td>{shipment.order_id}</td>
                    <td>{shipment.node_name}</td>
                    <td>{shipment.carrier_name}</td>
                    <td>{shipment.destination_city}</td>

                    <td>
                      {
                        String(
                          shipment.actual_delivery_date || ""
                        ).slice(0, 10) || "Pending"
                      }
                    </td>

                    <td>
                      <span
                        className={`status-badge ${statusClass(
                          shipment.shipment_status
                        )}`}
                      >
                        {shipment.shipment_status}
                      </span>
                    </td>

                    <td>
                      <button
                        className="view-button"
                        onClick={() =>
                          viewTracking(shipment.shipment_id)
                        }
                      >
                        <Eye size={16} />
                        View
                      </button>
                    </td>

                  </tr>
                ))}
              </tbody>

            </table>

          </div>
        )}

      </div>

      {/* Tracking modal */}
      {tracking && (
        <div className="modal-overlay">

          <div className="order-modal">

            <div className="modal-header">

              <div>
                <h2>Shipment Tracking</h2>
                <p>{selectedShipmentId}</p>
              </div>

              <button
                className="modal-close"
                onClick={() => {
                  setTracking(null);
                  setSelectedShipmentId("");
                  setEventType("");
                }}
              >
                <X size={21} />
              </button>

            </div>

            {/* Tracking history */}
            <h3 className="modal-section-title">
              Tracking Events
            </h3>

            {events.length === 0 ? (
              <p className="orders-message">
                No tracking events recorded yet.
              </p>
            ) : (
              <div className="table-scroll">

                <table className="data-table">

                  <thead>
                    <tr>
                      <th>Event</th>
                      <th>Time</th>
                      <th>Location</th>
                    </tr>
                  </thead>

                  <tbody>
                    {events.map((event, index) => (
                      <tr
                        key={event.tracking_event_id || index}
                      >
                        <td>{event.event_type}</td>

                        <td>
                          {String(event.event_time || "")
                            .replace("T", " ")
                            .slice(0, 19)}
                        </td>

                        <td>{event.event_location}</td>
                      </tr>
                    ))}
                  </tbody>

                </table>

              </div>
            )}

            {/* Add next tracking event */}
            {nextStages.length > 0 && (
              <>
                <h3 className="modal-section-title">
                  Add Tracking Event
                </h3>

                <form onSubmit={handleAddEvent}>

                  <div className="order-detail-grid">

                    <div>
                      <label>Event Type</label>

                      <select
                        value={eventType}
                        onChange={(e) =>
                          setEventType(e.target.value)
                        }
                        required
                      >
                        {nextStages.map((stage) => (
                          <option
                            key={stage}
                            value={stage}
                          >
                            {stage.replaceAll("_", " ")}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label>Event Time</label>

                      <input
                        type="datetime-local"
                        value={eventTime}
                        onChange={(e) =>
                          setEventTime(e.target.value)
                        }
                        required
                      />
                    </div>

                    <div>
                      <label>Event Location</label>

                      <input
                        type="text"
                        placeholder="Enter location"
                        value={eventLocation}
                        onChange={(e) =>
                          setEventLocation(e.target.value)
                        }
                        required
                      />
                    </div>

                  </div>

                  <button
                    type="submit"
                    className="modal-done-button"
                    disabled={savingEvent || !eventType}
                  >
                    <Clock size={17} />
                    {savingEvent ? "Saving..." : "Add Tracking Event"}
                  </button>

                </form>
              </>
            )}

            {nextStages.length === 0 && (
              <p className="orders-message">
                This shipment has completed its delivery journey.
              </p>
            )}

            <button
              className="modal-done-button"
              onClick={() => {
                setTracking(null);
                setSelectedShipmentId("");
                setEventType("");
              }}
            >
              Close
            </button>

          </div>
        </div>
      )}

    </div>
  );
}

export default Shipments;

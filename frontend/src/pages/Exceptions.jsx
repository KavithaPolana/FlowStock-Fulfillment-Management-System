
import { useEffect, useState } from "react";
import { RefreshCw, AlertTriangle, Search, ShieldAlert } from "lucide-react";
import { getExceptions, detectExceptions } from "../services/api";

function Exceptions() {
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("ALL");
  const [message, setMessage] = useState("");

  const loadExceptions = async () => {
    try {
      setLoading(true);
      const response = await getExceptions();
      setExceptions(response.data.exceptions || []);
    } catch (error) {
      console.error(error);
      setMessage("Unable to load exceptions. Check backend.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadExceptions();
  }, []);

  const handleDetect = async () => {
    try {
      setDetecting(true);
      setMessage("");

      const response = await detectExceptions();

      setMessage(response.data.message || "Exception detection completed.");
      await loadExceptions();
    } catch (error) {
      setMessage(
        error.response?.data?.message || "Exception detection failed."
      );
    } finally {
      setDetecting(false);
    }
  };

  const filteredExceptions = exceptions.filter((item) => {
    const text = `${item.exception_id} ${item.order_id || ""} ${
      item.shipment_id || ""
    } ${item.issue_type} ${item.description}`.toLowerCase();

    return (
      text.includes(search.toLowerCase()) &&
      (severity === "ALL" || item.severity === severity)
    );
  });

  const getSeverityClass = (value) => {
    if (value === "CRITICAL") return "status-delivered";
    if (value === "HIGH") return "status-transit";
    if (value === "MEDIUM") return "status-allocated";
    return "status-new";
  };

  return (
    <div className="orders-page">
      <div className="page-toolbar">
        <div>
          <h2>Exception Management</h2>
          <p>Detect and monitor fulfillment issues.</p>
        </div>

        <button className="refresh-button" onClick={loadExceptions}>
          <RefreshCw size={17} /> Refresh
        </button>
      </div>

      <div className="orders-summary">
        <div className="orders-summary-card">
          <AlertTriangle size={22} />
          <div>
            <strong>{exceptions.length}</strong>
            <span>Total Exceptions</span>
          </div>
        </div>

        <div className="orders-summary-card">
          <ShieldAlert size={22} />
          <div>
            <strong>
              {exceptions.filter(e => e.severity === "CRITICAL").length}
            </strong>
            <span>Critical</span>
          </div>
        </div>

        <div className="orders-summary-card">
          <AlertTriangle size={22} />
          <div>
            <strong>
              {exceptions.filter(e => e.severity === "HIGH").length}
            </strong>
            <span>High Severity</span>
          </div>
        </div>
      </div>

      {message && (
        <div className="allocation-message">
          {message}
        </div>
      )}

      <div className="orders-table-card">
        <div className="page-toolbar">
          <div>
            <h3>Detected Exceptions</h3>
            <p>Review issues affecting orders and shipments.</p>
          </div>

          <button
            className="view-button"
            onClick={handleDetect}
            disabled={detecting}
          >
            <AlertTriangle size={17} />
            {detecting ? "Detecting..." : "Detect Exceptions"}
          </button>
        </div>

        <div className="orders-filters">
          <div className="search-box">
            <Search size={18} />
            <input
              placeholder="Search order, shipment or issue..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        {loading ? (
          <p className="orders-message">Loading exceptions...</p>
        ) : (
          <>
            <div className="table-heading">
              <h3>Exception Records</h3>
              <span>{filteredExceptions.length} exceptions found</span>
            </div>

            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Exception ID</th>
                    <th>Order ID</th>
                    <th>Shipment ID</th>
                    <th>Issue Type</th>
                    <th>Severity</th>
                    <th>Description</th>
                    <th>Detected At</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredExceptions.map((item) => (
                    <tr key={item.exception_id}>
                      <td className="order-id-cell">{item.exception_id}</td>
                      <td>{item.order_id || "—"}</td>
                      <td>{item.shipment_id || "—"}</td>
                      <td>{item.issue_type}</td>
                      <td>
                        <span className={`status-badge ${getSeverityClass(item.severity)}`}>
                          {item.severity}
                        </span>
                      </td>
                      <td>{item.description}</td>
                      <td>
                        {String(item.detected_at || "")
                          .replace("T", " ")
                          .slice(0, 19)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {filteredExceptions.length === 0 && (
              <p className="orders-message">
                No matching exceptions found.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default Exceptions;

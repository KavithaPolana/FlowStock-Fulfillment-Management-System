
import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:5000/api",
  headers: {
    "Content-Type": "application/json",
  },
});

// Dashboard
export const getDashboard = () => API.get("/dashboard");

// Orders
export const getOrders = () => API.get("/orders");

export const getOrderDetails = (orderId) =>
  API.get(`/orders/${orderId}`);

export const allocateOrder = (orderId) =>
  API.post(`/orders/${orderId}/allocate`);

// Shipments
export const getShipments = () => API.get("/shipments");

export const createShipment = (orderId) =>
  API.post(`/orders/${orderId}/shipments`);

export const getShipmentTracking = (shipmentId) =>
  API.get(`/shipments/${shipmentId}/tracking`);

// Tracking
export const addTrackingEvent = (trackingData) =>
  API.post("/tracking", trackingData);

// Exceptions
export const getExceptions = () => API.get("/exceptions");

export const detectExceptions = () =>
  API.post("/exceptions/detect");

// Warehouses and Inventory
export const getWarehouses = () => API.get("/warehouses");

export const getInventory = (nodeId = "") =>
  API.get("/inventory", {
    params: nodeId ? { node_id: nodeId } : {},
  });

export default API;

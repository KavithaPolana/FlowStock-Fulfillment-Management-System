
import { useState } from "react";
import {
  BrowserRouter,
  Routes,
  Route,
  useLocation,
} from "react-router-dom";

import Sidebar from "./components/Sidebar";
import Header from "./components/Header";

import Dashboard from "./pages/Dashboard";
import Orders from "./pages/Orders";
import Allocation from "./pages/Allocation";
import Shipments from "./pages/Shipments";
import Exceptions from "./pages/Exceptions";
import Warehouses from "./pages/Warehouses";

const pageDetails = {
  "/": {
    title: "Dashboard",
    subtitle: "Welcome to your order fulfillment control center.",
  },
  "/orders": {
    title: "Orders Management",
    subtitle: "View and manage customer orders.",
  },
  "/allocation": {
    title: "Warehouse Allocation",
    subtitle: "Allocate orders to the most suitable fulfillment nodes.",
  },
  "/shipments": {
    title: "Shipments & Tracking",
    subtitle: "Monitor shipment progress and delivery status.",
  },
  "/exceptions": {
    title: "Exception Management",
    subtitle: "Monitor and investigate fulfillment issues.",
  },
  "/warehouses": {
    title: "Warehouses & Inventory",
    subtitle: "Monitor warehouse capacity and stock availability.",
  },
};

function AppLayout() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const location = useLocation();

  const currentPage =
    pageDetails[location.pathname] || pageDetails["/"];

  return (
    <div className="app-layout">
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      <main className="main-area">
        <Header
          title={currentPage.title}
          subtitle={currentPage.subtitle}
          onMenuClick={() => setIsSidebarOpen(true)}
        />

        <div className="page-container">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/allocation" element={<Allocation />} />
            <Route path="/shipments" element={<Shipments />} />
            <Route path="/exceptions" element={<Exceptions />} />
            <Route path="/warehouses" element={<Warehouses />} />
          </Routes>
        </div>

        <footer className="app-footer">
          <span>FlowStock Fulfillment Management System</span>
          <span>Smart Operations • Better Deliveries</span>
        </footer>
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}

export default App;

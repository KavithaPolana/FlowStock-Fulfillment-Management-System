
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ShoppingCart,
  GitBranch,
  Truck,
  AlertTriangle,
  Warehouse,
  Package,
  Leaf,
  X,
} from "lucide-react";

const menuItems = [
  { name: "Dashboard", path: "/", icon: LayoutDashboard },
  { name: "Orders", path: "/orders", icon: ShoppingCart },
  { name: "Allocation", path: "/allocation", icon: GitBranch },
  { name: "Shipments & Tracking", path: "/shipments", icon: Truck },
  { name: "Exceptions", path: "/exceptions", icon: AlertTriangle },
  { name: "Warehouses & Inventory", path: "/warehouses", icon: Warehouse },
];

function Sidebar({ isOpen, onClose }) {
  return (
    <>
      {isOpen && (
        <div className="sidebar-overlay" onClick={onClose}></div>
      )}

      <aside className={`sidebar ${isOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-icon">
            <Package size={24} />
          </div>

          <div className="brand-text">
            <h2>FlowStock</h2>
            <span>FULFILLMENT SYSTEM</span>
          </div>

          <button className="sidebar-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="sidebar-section-label">MAIN MENU</div>

        <nav className="sidebar-nav">
          {menuItems.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  `nav-item ${isActive ? "nav-item-active" : ""}`
                }
                onClick={onClose}
              >
                <Icon size={19} strokeWidth={1.8} />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="footer-leaf">
            <Leaf size={20} />
          </div>
          <div>
            <strong>Smart Fulfillment</strong>
            <p>Manage deliveries efficiently</p>
          </div>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;

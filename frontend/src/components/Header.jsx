
import { Menu, CalendarDays, Leaf } from "lucide-react";

function Header({ title, subtitle, onMenuClick }) {
  const today = new Date().toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  return (
    <header className="top-header">
      <div className="header-left">
        <button
          className="mobile-menu-button"
          onClick={onMenuClick}
          aria-label="Open navigation"
        >
          <Menu size={23} />
        </button>

        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
      </div>

      <div className="header-right">
        <div className="header-date">
          <CalendarDays size={17} />
          <span>{today}</span>
        </div>

        <div className="header-profile">
          <div className="profile-icon">
            <Leaf size={19} />
          </div>
          <div className="profile-info">
            <strong>Admin</strong>
            <span>Operations</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;

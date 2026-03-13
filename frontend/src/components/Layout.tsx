/**
 * Root layout — sidebar navigation + content outlet.
 */
import { NavLink, Outlet } from "react-router-dom";
import {
  MessageSquare,
  Bot,
  Brain,
  Activity,
  Clock,
  Shield,
  Settings,
  Menu,
} from "lucide-react";
import { useUIStore } from "../store/uiStore";
import clsx from "clsx";

const navItems = [
  { to: "/", icon: MessageSquare, label: "Chat" },
  { to: "/sessions", icon: Clock, label: "Sessions" },
  { to: "/agents", icon: Bot, label: "Agents" },
  { to: "/memory", icon: Brain, label: "Memory" },
  { to: "/traces", icon: Activity, label: "Traces" },
  { to: "/admin", icon: Shield, label: "Admin" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Layout() {
  const { sidebarOpen, toggleSidebar } = useUIStore();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside
        className={clsx(
          "flex flex-col bg-gray-900 border-r border-gray-800 transition-all duration-200",
          sidebarOpen ? "w-56" : "w-16"
        )}
      >
        <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-800">
          <button
            onClick={toggleSidebar}
            className="p-1 rounded hover:bg-gray-800"
          >
            <Menu size={20} />
          </button>
          {sidebarOpen && (
            <span className="text-sm font-semibold tracking-wide text-primary-400">
              COS-AA
            </span>
          )}
        </div>

        <nav className="flex-1 py-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 mx-2 px-3 py-2 rounded-lg text-sm transition-colors",
                  isActive
                    ? "bg-primary-600/20 text-primary-400"
                    : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
                )
              }
            >
              <Icon size={18} />
              {sidebarOpen && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-500">
          {sidebarOpen ? "v2.0.0" : "v2"}
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto bg-gray-950">
        <Outlet />
      </main>
    </div>
  );
}

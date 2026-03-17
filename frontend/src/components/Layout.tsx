/**
 * Root layout — responsive sidebar navigation + content outlet.
 * Desktop: collapsible sidebar. Mobile: slide-out drawer with backdrop.
 */
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  MessageSquare,
  Bot,
  Brain,
  Activity,
  Clock,
  Shield,
  ShieldCheck,
  Zap,
  Settings,
  Menu,
  LogOut,
  Lock,
  X,
} from "lucide-react";
import { useUIStore } from "../store/uiStore";
import { useAuthStore } from "../store/authStore";
import EmailVerificationBanner from "./EmailVerificationBanner";
import clsx from "clsx";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/chat", icon: MessageSquare, label: "Chat" },
  { to: "/sessions", icon: Clock, label: "Sessions" },
  { to: "/agents", icon: Bot, label: "Agents" },
  { to: "/memory", icon: Brain, label: "Memory" },
  { to: "/traces", icon: Activity, label: "Traces" },
  { to: "/admin", icon: Shield, label: "Admin" },
  { to: "/security", icon: Lock, label: "Security" },
  { to: "/security-audit", icon: ShieldCheck, label: "Audit" },
  { to: "/load-test", icon: Zap, label: "Load Test" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export default function Layout() {
  const { sidebarOpen, mobileMenuOpen, toggleSidebar, setMobileMenu } =
    useUIStore();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = async () => {
    setMobileMenu(false);
    await logout();
    navigate("/login", { replace: true });
  };

  const closeMobile = () => setMobileMenu(false);

  /* ---- Shared sidebar content ---- */
  const sidebarContent = (isMobile: boolean) => {
    const expanded = isMobile || sidebarOpen;

    return (
      <>
        <div className="flex items-center gap-3 px-4 py-4 border-b border-gray-800">
          {isMobile ? (
            <>
              <span className="text-sm font-semibold tracking-wide text-primary-400 flex-1">
                COS-AA
              </span>
              <button
                onClick={closeMobile}
                className="p-1 rounded hover:bg-gray-800"
              >
                <X size={20} />
              </button>
            </>
          ) : (
            <>
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
            </>
          )}
        </div>

        <nav className="flex-1 py-4 space-y-1 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={isMobile ? closeMobile : undefined}
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
              {expanded && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User info + Logout */}
        <div className="border-t border-gray-800">
          {expanded && user && (
            <div className="px-4 pt-3 pb-1">
              <p className="text-xs text-gray-400 truncate">{user.email}</p>
              <p className="text-[10px] text-gray-600 capitalize">
                {user.role}
              </p>
            </div>
          )}
          <button
            onClick={handleLogout}
            className={clsx(
              "flex items-center gap-3 w-full px-4 py-3 text-sm text-gray-400 hover:bg-red-900/20 hover:text-red-400 transition-colors",
              !expanded && "justify-center"
            )}
            title="Log out"
          >
            <LogOut size={18} />
            {expanded && <span>Log out</span>}
          </button>
        </div>

        <div className="px-4 py-2 border-t border-gray-800 text-xs text-gray-500">
          {expanded ? "v2.0.0" : "v2"}
        </div>
      </>
    );
  };

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ---- Mobile backdrop ---- */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden"
          onClick={closeMobile}
        />
      )}

      {/* ---- Mobile drawer ---- */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 w-64 flex flex-col bg-gray-900 border-r border-gray-800 transition-transform duration-200 md:hidden",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {sidebarContent(true)}
      </aside>

      {/* ---- Desktop sidebar ---- */}
      <aside
        className={clsx(
          "hidden md:flex flex-col bg-gray-900 border-r border-gray-800 transition-all duration-200",
          sidebarOpen ? "w-56" : "w-16"
        )}
      >
        {sidebarContent(false)}
      </aside>

      {/* ---- Main content ---- */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Mobile top bar */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800 bg-gray-900 md:hidden">
          <button
            onClick={() => setMobileMenu(true)}
            className="p-1 rounded hover:bg-gray-800"
          >
            <Menu size={20} />
          </button>
          <span className="text-sm font-semibold tracking-wide text-primary-400">
            COS-AA
          </span>
        </div>

        <main className="flex-1 overflow-y-auto bg-gray-950">
          <EmailVerificationBanner />
          <Outlet />
        </main>
      </div>
    </div>
  );
}

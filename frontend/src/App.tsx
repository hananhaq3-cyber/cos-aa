import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import ChatPage from "./pages/ChatPage";
import DashboardPage from "./pages/DashboardPage";
import AgentsPage from "./pages/AgentsPage";
import AgentDetailPage from "./pages/AgentDetailPage";
import MemoryPage from "./pages/MemoryPage";
import TracesPage from "./pages/TracesPage";
import SessionsPage from "./pages/SessionsPage";
import AdminPage from "./pages/AdminPage";
import SettingsPage from "./pages/SettingsPage";
import SecurityPage from "./pages/SecurityPage";
import SecurityAuditPage from "./pages/SecurityAuditPage";
import LoadTestPage from "./pages/LoadTestPage";
import LoginPage from "./pages/LoginPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import OAuthVerifyPage from "./pages/OAuthVerifyPage";
import { useAuthStore } from "./store/authStore";

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/oauth-verify" element={<OAuthVerifyPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="agents/:definitionId" element={<AgentDetailPage />} />
          <Route path="memory" element={<MemoryPage />} />
          <Route path="traces" element={<TracesPage />} />
          <Route path="admin" element={<AdminPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="security" element={<SecurityPage />} />
          <Route path="security-audit" element={<SecurityAuditPage />} />
          <Route path="load-test" element={<LoadTestPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

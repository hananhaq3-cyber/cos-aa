import { useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import ChatPage from "./pages/ChatPage";
import AgentsPage from "./pages/AgentsPage";
import MemoryPage from "./pages/MemoryPage";
import TracesPage from "./pages/TracesPage";
import SessionsPage from "./pages/SessionsPage";
import AdminPage from "./pages/AdminPage";
import SettingsPage from "./pages/SettingsPage";
import LoginPage from "./pages/LoginPage";
import { useAuthStore } from "./store/authStore";

export default function App() {
  const hydrate = useAuthStore((s) => s.hydrate);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Layout />}>
          <Route index element={<ChatPage />} />
          <Route path="sessions" element={<SessionsPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="memory" element={<MemoryPage />} />
          <Route path="traces" element={<TracesPage />} />
          <Route path="admin" element={<AdminPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

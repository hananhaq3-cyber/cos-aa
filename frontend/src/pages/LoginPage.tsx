import { useEffect, lazy, Suspense } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import AuthCard from "../components/login/AuthCard";
import { useAuthStore } from "../store/authStore";

const NeuralBackground = lazy(
  () => import("../components/login/NeuralBackground")
);

export default function LoginPage() {
  const { isAuthenticated, login } = useAuthStore();
  const navigate = useNavigate();
  const [params] = useSearchParams();

  useEffect(() => {
    const token = params.get("token");
    if (token) {
      login(token);
      navigate("/", { replace: true });
      return;
    }
    if (isAuthenticated) {
      navigate("/", { replace: true });
    }
  }, [isAuthenticated, login, navigate, params]);

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-gray-950">
      {/* 3D Neural Network */}
      <Suspense fallback={null}>
        <NeuralBackground />
      </Suspense>

      {/* Top gradient overlay */}
      <div className="pointer-events-none fixed inset-x-0 top-0 h-40 bg-gradient-to-b from-gray-950 to-transparent" />

      {/* Bottom gradient overlay */}
      <div className="pointer-events-none fixed inset-x-0 bottom-0 h-40 bg-gradient-to-t from-gray-950 to-transparent" />

      {/* Radial vignette */}
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_at_center,transparent_30%,rgba(3,7,18,0.7)_100%)]" />

      {/* Subtle radial glow behind card */}
      <div className="pointer-events-none absolute h-[500px] w-[500px] rounded-full bg-blue-600/[0.04] blur-[100px]" />

      {/* Auth Card with fade-in */}
      <div className="relative z-10 animate-[fadeIn_0.8s_ease-out]">
        <AuthCard />
      </div>
    </div>
  );
}

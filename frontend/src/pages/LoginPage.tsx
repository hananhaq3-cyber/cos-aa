import { useEffect, lazy, Suspense, useState, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import AuthCard from "../components/login/AuthCard";
import { useAuthStore } from "../store/authStore";
import { getMe } from "../api/auth";

const NeuralBackground = lazy(
  () => import("../components/login/NeuralBackground")
);

export default function LoginPage() {
  const { isAuthenticated, login } = useAuthStore();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [checkingAuth, setCheckingAuth] = useState(true);
  const hasCheckedAuth = useRef(false);

  // Handle OAuth error redirects
  const oauthError = params.get("error");

  useEffect(() => {
    // Prevent multiple runs of auth validation
    if (hasCheckedAuth.current) {
      return;
    }

    // Check for token in URL (OAuth callback with token)
    const tokenParam = params.get("token");
    if (tokenParam) {
      hasCheckedAuth.current = true;
      login(tokenParam);
      navigate("/", { replace: true });
      return;
    }

    // If already authenticated via localStorage, redirect to dashboard
    if (isAuthenticated) {
      hasCheckedAuth.current = true;
      navigate("/", { replace: true });
      return;
    }

    // Only call getMe() once to check for HTTP-only cookie auth
    const validateCookieAuth = async () => {
      if (hasCheckedAuth.current) return;
      hasCheckedAuth.current = true;

      try {
        const user = await getMe();
        if (user && user.access_token) {
          login(user.access_token);
          navigate("/", { replace: true });
        } else {
          setCheckingAuth(false);
        }
      } catch {
        // Not authenticated via cookie, show login form
        setCheckingAuth(false);
      }
    };

    validateCookieAuth();
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
      <div className="relative z-10 w-full px-4 sm:px-0 flex justify-center animate-[fadeIn_0.8s_ease-out]">
        {checkingAuth ? (
          <div className="text-center text-gray-400">Checking authentication...</div>
        ) : (
          <>
            {oauthError && (
              <div className="mb-4 p-3 bg-red-900/30 border border-red-500/40 rounded-lg text-sm text-red-400 text-center">
                {oauthError === "invalid_state"
                  ? "OAuth session expired. Please try again."
                  : oauthError === "account_exists_with_different_provider"
                  ? "This email already has an account with a different login method. Please use your original login method."
                  : "OAuth sign-in failed. Please try again."}
              </div>
            )}
            <AuthCard />
          </>
        )}
      </div>
    </div>
  );
}

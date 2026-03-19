import { useState, useEffect, useRef, lazy, Suspense } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { CheckCircle, XCircle, Loader2, Mail, ArrowLeft } from "lucide-react";
import { useAuthStore } from "../store/authStore";
import { verifyOAuthCode } from "../api/auth";

const NeuralBackground = lazy(
  () => import("../components/login/NeuralBackground")
);

export default function OAuthVerifyPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuthStore();

  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const sessionId = params.get("session");
  const provider = params.get("provider") || "OAuth";
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Redirect if no session ID
    if (!sessionId) {
      navigate("/login", { replace: true });
      return;
    }

    // Focus input on mount
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [sessionId, navigate]);

  const handleCodeChange = (value: string) => {
    // Only allow numbers and limit to 6 digits
    const numericValue = value.replace(/\D/g, "").slice(0, 6);
    setCode(numericValue);
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (code.length !== 6) {
      setError("Please enter the complete 6-digit code");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const data = await verifyOAuthCode(sessionId, code);

      setSuccess(true);
      login(data.access_token);

      // Navigate after a short delay for user feedback
      setTimeout(() => {
        navigate("/", { replace: true });
      }, 1500);
    } catch (err: any) {
      const errorMessage =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        err?.message ||
        "Invalid verification code";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    // TODO: Implement resend functionality
    setError("Resend feature coming soon. Please check your email.");
  };

  const formatCode = (value: string) => {
    // Add spaces for readability: 123 456
    return value.replace(/(\d{3})(\d{1,3})/, "$1 $2");
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <Suspense fallback={null}>
        <NeuralBackground />
      </Suspense>

      <div className="relative z-10 w-full max-w-md mx-auto p-6 sm:p-8 bg-gray-900/80 backdrop-blur-sm border border-gray-800 rounded-2xl">
        {!success ? (
          <>
            <div className="text-center mb-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-full mb-4">
                <Mail className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-2xl font-semibold text-white mb-2">
                Verify Your {provider.charAt(0).toUpperCase() + provider.slice(1)} Sign-in
              </h1>
              <p className="text-sm text-gray-400">
                We've sent a 6-digit verification code to your email address.
                Enter it below to complete your sign-in.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="code" className="block text-sm font-medium text-gray-300 mb-2">
                  Verification Code
                </label>
                <input
                  ref={inputRef}
                  type="text"
                  id="code"
                  value={formatCode(code)}
                  onChange={(e) => handleCodeChange(e.target.value)}
                  placeholder="000 000"
                  className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-lg text-white text-center text-2xl font-mono tracking-widest focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 outline-none transition-all"
                  maxLength={7} // 6 digits + 1 space
                  autoComplete="one-time-code"
                  inputMode="numeric"
                />
                <p className="text-xs text-gray-500 mt-2">
                  Code expires in 10 minutes
                </p>
              </div>

              {error && (
                <div className="p-3 bg-red-900/30 border border-red-700/50 rounded-lg">
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || code.length !== 6}
                className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  "Verify & Sign In"
                )}
              </button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-gray-400 mb-2">
                Didn't receive the code?
              </p>
              <button
                onClick={handleResendCode}
                className="text-sm text-blue-400 hover:text-blue-300 font-medium transition-colors"
              >
                Resend Code
              </button>
            </div>

            <div className="mt-6 pt-6 border-t border-gray-800">
              <button
                onClick={() => navigate("/login")}
                className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-300 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Sign In
              </button>
            </div>
          </>
        ) : (
          <div className="text-center">
            <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
            <h1 className="text-2xl font-semibold text-white mb-2">
              Verification Successful!
            </h1>
            <p className="text-sm text-gray-400 mb-4">
              Your {provider} account has been verified. You're being signed in...
            </p>
            <Loader2 className="w-6 h-6 text-blue-400 animate-spin mx-auto" />
          </div>
        )}
      </div>
    </div>
  );
}
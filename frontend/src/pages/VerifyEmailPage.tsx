import { useEffect, useState, lazy, Suspense } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";
import { verifyEmail } from "../api/auth";

const NeuralBackground = lazy(
  () => import("../components/login/NeuralBackground")
);

type Status = "loading" | "success" | "error";

export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState<Status>("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const token = params.get("token");
    if (!token) {
      setStatus("error");
      setMessage("Missing verification token.");
      return;
    }

    verifyEmail(token)
      .then((res) => {
        setStatus("success");
        setMessage(res.message || "Email verified successfully!");
      })
      .catch((err) => {
        setStatus("error");
        const msg =
          err?.response?.data?.detail ||
          err?.response?.data?.error ||
          "Verification failed. The link may be expired or invalid.";
        setMessage(msg);
      });
  }, [params]);

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <Suspense fallback={null}>
        <NeuralBackground />
      </Suspense>
      <div className="relative z-10 w-full max-w-md mx-auto p-6 sm:p-8 bg-gray-900/80 backdrop-blur-sm border border-gray-800 rounded-2xl text-center">
        {status === "loading" && (
          <>
            <Loader2 size={48} className="mx-auto text-primary-400 animate-spin mb-4" />
            <h1 className="text-xl font-semibold text-white mb-2">Verifying your email...</h1>
            <p className="text-sm text-gray-400">Please wait while we confirm your address.</p>
          </>
        )}

        {status === "success" && (
          <>
            <CheckCircle size={48} className="mx-auto text-green-400 mb-4" />
            <h1 className="text-xl font-semibold text-white mb-2">Email Verified!</h1>
            <p className="text-sm text-gray-400 mb-6">{message}</p>
            <button
              onClick={() => navigate("/login", { replace: true })}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Continue to Login
            </button>
          </>
        )}

        {status === "error" && (
          <>
            <XCircle size={48} className="mx-auto text-red-400 mb-4" />
            <h1 className="text-xl font-semibold text-white mb-2">Verification Failed</h1>
            <p className="text-sm text-gray-400 mb-6">{message}</p>
            <button
              onClick={() => navigate("/login", { replace: true })}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Go to Login
            </button>
          </>
        )}
      </div>
    </div>
  );
}

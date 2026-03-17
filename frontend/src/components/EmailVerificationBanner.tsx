import { useState } from "react";
import { AlertTriangle, X, Loader2 } from "lucide-react";
import { resendVerification } from "../api/auth";
import { useAuthStore } from "../store/authStore";

export default function EmailVerificationBanner() {
  const user = useAuthStore((s) => s.user);
  const [dismissed, setDismissed] = useState(false);
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");

  if (!user || user.email_verified || dismissed) return null;

  const handleResend = async () => {
    setSending(true);
    setMessage("");
    try {
      const res = await resendVerification();
      setMessage(res.message);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.response?.data?.error ||
        "Failed to send verification email";
      setMessage(msg);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="bg-yellow-900/30 border-b border-yellow-700/50 px-4 py-3 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3 min-w-0">
        <AlertTriangle size={18} className="text-yellow-400 shrink-0" />
        <p className="text-sm text-yellow-200 truncate">
          Please verify your email address to access all features.
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {message && (
          <span className="text-xs text-yellow-300">{message}</span>
        )}
        <button
          onClick={handleResend}
          disabled={sending}
          className="px-3 py-1 text-xs font-medium bg-yellow-600 hover:bg-yellow-500 text-white rounded transition-colors disabled:opacity-50"
        >
          {sending ? <Loader2 size={14} className="animate-spin" /> : "Resend"}
        </button>
        <button
          onClick={() => setDismissed(true)}
          className="p-1 text-yellow-400 hover:text-yellow-200 transition-colors"
          title="Dismiss"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
}

/**
 * Main chat page — send messages, view OODA progress, see responses, handle confirmations.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Send, CheckCircle, XCircle } from "lucide-react";
import { useSessionStore } from "../store/sessionStore";
import { createSession, sendMessage, confirmSession } from "../api/endpoints";
import { subscribeToOODAProgress } from "../api/socket";
import ChatBubble from "../components/ChatBubble";
import PhaseIndicator from "../components/PhaseIndicator";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [confirmLoading, setConfirmLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const {
    currentSession,
    messages,
    currentPhase,
    isProcessing,
    pendingConfirmation,
    proposedAction,
    setSession,
    addMessage,
    setPhase,
    setProcessing,
    addCycleResult,
    setPendingConfirmation,
  } = useSessionStore();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(scrollToBottom, [messages, scrollToBottom]);

  // Subscribe to OODA progress when session exists
  useEffect(() => {
    if (!currentSession) return;

    const unsubscribe = subscribeToOODAProgress(
      currentSession.session_id,
      (progress) => {
        setPhase(progress.phase);
      }
    );

    return unsubscribe;
  }, [currentSession, setPhase]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isProcessing || pendingConfirmation) return;

    setInput("");
    setProcessing(true);

    try {
      // Create session if needed
      let session = currentSession;
      if (!session) {
        session = await createSession(text);
        setSession(session);
      }

      // Add user message to UI
      addMessage({
        message_id: crypto.randomUUID(),
        session_id: session.session_id,
        role: "USER",
        content: text,
        created_at: new Date().toISOString(),
      });

      // Send message and get OODA result
      setPhase("OBSERVING");
      const result = await sendMessage(session.session_id, text);
      addCycleResult(result);

      // Check if confirmation is needed
      if (result.pending_confirmation) {
        setPendingConfirmation(true, result.proposed_action);
        setPhase("AWAITING_CONFIRMATION");
      } else {
        // Add assistant response
        addMessage({
          message_id: crypto.randomUUID(),
          session_id: session.session_id,
          role: "ASSISTANT",
          content: result.evidence || "Cycle completed.",
          created_at: new Date().toISOString(),
        });
        setPhase(result.goal_achieved ? "COMPLETE" : "IDLE");
      }
    } catch (err) {
      addMessage({
        message_id: crypto.randomUUID(),
        session_id: currentSession?.session_id || "",
        role: "SYSTEM",
        content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        created_at: new Date().toISOString(),
      });
      setPhase("IDLE");
    } finally {
      setProcessing(false);
    }
  };

  const handleConfirm = async (decision: "approved" | "rejected") => {
    if (!currentSession || confirmLoading) return;

    setConfirmLoading(true);
    try {
      const result = await confirmSession(currentSession.session_id, decision);

      // Add confirmation message
      addMessage({
        message_id: crypto.randomUUID(),
        session_id: currentSession.session_id,
        role: "SYSTEM",
        content: `Action ${decision === "approved" ? "approved ✓" : "rejected ✗"}`,
        created_at: new Date().toISOString(),
      });

      // Add assistant response from the result
      addMessage({
        message_id: crypto.randomUUID(),
        session_id: currentSession.session_id,
        role: "ASSISTANT",
        content: result.evidence || "Confirmation processed.",
        created_at: new Date().toISOString(),
      });

      setPendingConfirmation(false);
      setPhase(result.goal_achieved ? "COMPLETE" : "IDLE");
    } catch (err) {
      addMessage({
        message_id: crypto.randomUUID(),
        session_id: currentSession.session_id,
        role: "SYSTEM",
        content: `Confirmation error: ${err instanceof Error ? err.message : "Unknown error"}`,
        created_at: new Date().toISOString(),
      });
    } finally {
      setConfirmLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-4 sm:px-6 py-4 border-b border-gray-800">
        <div>
          <h1 className="text-lg font-semibold">Chat</h1>
          <p className="text-xs text-gray-500">
            {currentSession
              ? `Session: ${currentSession.session_id.slice(0, 8)}...`
              : "Start a conversation"}
          </p>
        </div>
      </header>

      {/* OODA phase indicator */}
      {isProcessing && (
        <div className="border-b border-gray-800 bg-gray-900/50">
          <PhaseIndicator currentPhase={currentPhase} />
        </div>
      )}

      {/* Pending Confirmation Banner */}
      {pendingConfirmation && (
        <div className="border-b border-yellow-500/30 bg-yellow-900/20 px-4 sm:px-6 py-4">
          <div className="mb-3">
            <p className="text-sm font-medium text-yellow-200 mb-2">
              ⚠️ Awaiting Your Confirmation
            </p>
            {proposedAction && (
              <p className="text-sm text-yellow-100">
                Proposed action: {proposedAction}
              </p>
            )}
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => handleConfirm("approved")}
              disabled={confirmLoading}
              className="flex items-center gap-2 px-3 py-2 bg-green-600 hover:bg-green-500 disabled:bg-gray-700 text-sm rounded-lg transition-colors"
            >
              <CheckCircle size={16} />
              Approve
            </button>
            <button
              onClick={() => handleConfirm("rejected")}
              disabled={confirmLoading}
              className="flex items-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 text-sm rounded-lg transition-colors"
            >
              <XCircle size={16} />
              Reject
            </button>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <p className="text-lg mb-2">Welcome to COS-AA</p>
            <p className="text-sm">
              Send a message to start an OODA reasoning cycle.
            </p>
          </div>
        )}
        {messages.map((msg) => (
          <ChatBubble
            key={msg.message_id}
            role={msg.role}
            content={typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content)}
            timestamp={msg.created_at}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 sm:px-6 py-4 border-t border-gray-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={pendingConfirmation ? "Awaiting confirmation..." : "Type your message..."}
            disabled={isProcessing || pendingConfirmation}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isProcessing || pendingConfirmation || !input.trim()}
            className="p-3 bg-primary-600 hover:bg-primary-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-xl transition-colors"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}

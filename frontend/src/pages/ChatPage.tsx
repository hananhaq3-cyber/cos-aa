/**
 * Main chat page — send messages, view OODA progress, see responses.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { useSessionStore } from "../store/sessionStore";
import { createSession, sendMessage } from "../api/endpoints";
import { subscribeToOODAProgress } from "../api/socket";
import ChatBubble from "../components/ChatBubble";
import PhaseIndicator from "../components/PhaseIndicator";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const {
    currentSession,
    messages,
    currentPhase,
    isProcessing,
    setSession,
    addMessage,
    setPhase,
    setProcessing,
    addCycleResult,
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
    if (!text || isProcessing) return;

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

      // Add assistant response
      addMessage({
        message_id: crypto.randomUUID(),
        session_id: session.session_id,
        role: "ASSISTANT",
        content: result.evidence || "Cycle completed.",
        created_at: new Date().toISOString(),
      });

      setPhase(result.goal_achieved ? "COMPLETE" : "IDLE");
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

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
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

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
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
      <div className="px-6 py-4 border-t border-gray-800">
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
            placeholder="Type your message..."
            disabled={isProcessing}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-primary-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isProcessing || !input.trim()}
            className="p-3 bg-primary-600 hover:bg-primary-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded-xl transition-colors"
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}

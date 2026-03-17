/**
 * Socket.IO client for real-time OODA progress streaming, message delivery, and session updates.
 */
import { io, Socket } from "socket.io-client";
import type { OODAProgress, Message } from "../types";

let socket: Socket | null = null;

export function connectSocket(): Socket {
  if (socket?.connected) return socket;

  socket = io("/", {
    path: "/ws/socket.io",
    transports: ["websocket", "polling"],
    auth: {
      token: localStorage.getItem("cos_aa_token") || "",
    },
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionAttempts: 10,
  });

  socket.on("connect", () => {
    console.log("[WS] Connected:", socket?.id);
  });

  socket.on("disconnect", (reason) => {
    console.log("[WS] Disconnected:", reason);
  });

  socket.on("error", (error) => {
    console.error("[WS] Error:", error);
  });

  return socket;
}

// ── OODA Progress ──

export function subscribeToOODAProgress(
  sessionId: string,
  callback: (progress: OODAProgress) => void
): () => void {
  const sock = connectSocket();
  const channel = `ooda:progress:${sessionId}`;

  sock.on(channel, callback);

  return () => {
    sock.off(channel, callback);
  };
}

// ── Message Events ──

export function subscribeToMessages(
  sessionId: string,
  callback: (message: Message) => void
): () => void {
  const sock = connectSocket();
  const channel = `message:${sessionId}`;

  sock.on(channel, callback);

  return () => {
    sock.off(channel, callback);
  };
}

// ── Session Status Updates ──

export function subscribeToSessionStatus(
  sessionId: string,
  callback: (status: { status: string; goal_achieved?: boolean; completed_at?: string }) => void
): () => void {
  const sock = connectSocket();
  const channel = `session:status:${sessionId}`;

  sock.on(channel, callback);

  return () => {
    sock.off(channel, callback);
  };
}

// ── Connection Management ──

export function disconnectSocket(): void {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}

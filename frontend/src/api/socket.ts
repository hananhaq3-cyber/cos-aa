/**
 * Socket.IO client for real-time OODA progress streaming.
 */
import { io, Socket } from "socket.io-client";
import type { OODAProgress } from "../types";

let socket: Socket | null = null;

export function connectSocket(): Socket {
  if (socket?.connected) return socket;

  socket = io("/", {
    path: "/ws/socket.io",
    transports: ["websocket", "polling"],
    auth: {
      token: localStorage.getItem("cos_aa_token") || "",
    },
  });

  socket.on("connect", () => {
    console.log("[WS] Connected:", socket?.id);
  });

  socket.on("disconnect", (reason) => {
    console.log("[WS] Disconnected:", reason);
  });

  return socket;
}

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

export function disconnectSocket(): void {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}

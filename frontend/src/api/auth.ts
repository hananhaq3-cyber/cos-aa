import api from "./client";
import type {
  AuthResponse,
  LoginRequest,
  RegisterRequest,
  SessionInfo,
} from "../types/auth";

export async function loginWithCredentials(
  data: LoginRequest
): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/login", data);
  return res.data;
}

export async function register(
  data: RegisterRequest
): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/register", data);
  return res.data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
}

export async function getSessions(): Promise<SessionInfo[]> {
  const res = await api.get<SessionInfo[]>("/auth/sessions");
  return res.data;
}

export async function revokeSession(jti: string): Promise<void> {
  await api.post(`/auth/sessions/${jti}/revoke`);
}

export async function revokeAllSessions(): Promise<void> {
  await api.post("/auth/sessions/revoke-all");
}

export function getOAuthUrl(provider: "google" | "github" | "apple"): string {
  const baseUrl = import.meta.env.VITE_API_URL || "";
  return `${baseUrl}/api/v1/auth/${provider}`;
}

export async function verifyEmail(token: string): Promise<{ message: string }> {
  const res = await api.get<{ message: string }>(`/auth/verify-email?token=${encodeURIComponent(token)}`);
  return res.data;
}

export async function resendVerification(): Promise<{ message: string }> {
  const res = await api.post<{ message: string }>("/auth/resend-verification");
  return res.data;
}

export async function verifyOAuthCode(sessionId: string, code: string): Promise<AuthResponse> {
  const res = await api.post<AuthResponse>("/auth/oauth-verify", {
    session_id: sessionId,
    code: code,
  });
  return res.data;
}

export async function getMe(): Promise<AuthResponse> {
  const res = await api.get<AuthResponse>("/auth/me");
  return res.data;
}

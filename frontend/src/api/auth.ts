import api from "./client";
import type { AuthResponse, LoginRequest, RegisterRequest } from "../types/auth";

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

export function getOAuthUrl(provider: "google" | "github" | "apple"): string {
  return `/api/v1/auth/${provider}`;
}

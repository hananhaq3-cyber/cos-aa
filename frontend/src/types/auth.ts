export interface User {
  user_id: string;
  tenant_id: string;
  email: string;
  role: string;
  email_verified: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  tenant_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  tenant_id: string;
  email: string;
  role: string;
  expires_in: number;
  jti?: string;
  email_verified: boolean;
}

export interface SessionInfo {
  id: string;
  jti: string;
  user_agent: string | null;
  ip_address: string | null;
  country: string | null;
  created_at: string;
  expires_at: string;
  last_activity_at: string | null;
  is_current: boolean;
  is_revoked: boolean;
}

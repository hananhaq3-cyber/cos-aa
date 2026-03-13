export interface User {
  user_id: string;
  tenant_id: string;
  email: string;
  role: string;
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
}

import { create } from "zustand";
import type { User } from "../types/auth";

const TOKEN_KEY = "cos_aa_token";

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => void;
  logout: () => void;
  hydrate: () => void;
}

function parseJwtPayload(token: string): User | null {
  try {
    const base64 = token.split(".")[1];
    const json = atob(base64);
    const payload = JSON.parse(json);
    // Check expiration
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      return null;
    }
    return {
      user_id: payload.sub,
      tenant_id: payload.tenant_id,
      email: payload.email ?? "",
      role: payload.role,
    };
  } catch {
    return null;
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    const user = parseJwtPayload(token);
    set({ token, user, isAuthenticated: !!user, isLoading: false });
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ token: null, user: null, isAuthenticated: false, isLoading: false });
  },

  hydrate: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      const user = parseJwtPayload(token);
      if (user) {
        set({ token, user, isAuthenticated: true, isLoading: false });
        return;
      }
      // Token expired — remove it
      localStorage.removeItem(TOKEN_KEY);
    }
    set({ token: null, user: null, isAuthenticated: false, isLoading: false });
  },
}));

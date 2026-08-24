/**
 * authStore.ts — Zustand store holding the CURRENT session.
 *
 * STORES:
 *   accessToken: string | null      — JWT bearer token
 *   user: CurrentUser | null        — id, email, role, mfaEnabled, isFirstLogin
 *   status: "loading" | "authed" | "anon"
 *
 * PROTOTYPE SIMPLIFICATION:
 *   The token is persisted to localStorage so a page reload keeps you logged in without a
 *   refresh-token flow. This is a known prototype trade-off (localStorage is XSS-readable).
 *   Production moves to an in-memory access token + an httpOnly refresh cookie — see
 *   feature_plans/auth_plan.md. Keep the key name below so the swap is one place.
 *
 * ACTIONS:
 *   setSession(accessToken, user)   — after login/MFA; also writes localStorage
 *   clear()                         — logout / 401; also clears localStorage
 */
import { create } from "zustand";
import type { CurrentUser } from "../types";

const TOKEN_KEY = "dms_access_token";

interface AuthState {
  accessToken: string | null;
  user: CurrentUser | null;
  status: "loading" | "authed" | "anon";
  setSession: (accessToken: string, user: CurrentUser) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem(TOKEN_KEY),
  user: null,
  status: "loading",
  setSession: (accessToken, user) => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    set({ accessToken, user, status: "authed" });
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    set({ accessToken: null, user: null, status: "anon" });
  },
}));

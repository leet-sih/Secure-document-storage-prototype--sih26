/**
 * AuthContext.tsx — React Context + useReducer session store.
 * Replaces authStore.ts (Zustand). See CHANGES.md §5.
 *
 * STORES:
 *   user: CurrentUser | null      — id, email, role, mfaEnabled, isFirstLogin
 *   status: "loading" | "authed" | "anon"
 *
 * TOKEN STRATEGY:
 *   The JWT access token is stored in localStorage (dms_access_token) for prototype
 *   convenience. It is read directly by apiFetch() in lib/apiClient.ts — the HTTP layer
 *   does not need to go through a React context to get the token, which means apiFetch
 *   works outside the component tree too.
 *   Production: move to in-memory token + httpOnly refresh cookie (see auth_plan.md).
 *
 * ACTIONS:
 *   setSession(accessToken, user)   — after login/step-up MFA; writes localStorage
 *   clear()                         — logout / 401; clears localStorage
 *
 * STEP-UP MFA:
 *   After POST /auth/mfa/step-up returns a re-stamped token, call setSession() with the
 *   new token. The AuthContext does not track mfa_at itself — that claim lives inside the
 *   JWT and is checked server-side by @require_recent_mfa. See feature_plans/auth_plan.md.
 *
 * USAGE:
 *   Wrap <App> in <AuthProvider>. Components call useAuth() to read state or dispatch.
 *   TODO: implement all stubs below.
 */

import { createContext, useContext, useReducer } from "react";
import type { ReactNode } from "react";
import type { CurrentUser } from "../types";

export const TOKEN_KEY = "dms_access_token";

// ── State ──────────────────────────────────────────────────────────

interface AuthState {
  user: CurrentUser | null;
  status: "loading" | "authed" | "anon";
}

const initialState: AuthState = {
  user: null,
  status: "loading",
};

// ── Actions ────────────────────────────────────────────────────────

type AuthAction =
  | { type: "SET_SESSION"; user: CurrentUser }
  | { type: "CLEAR" };

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "SET_SESSION":
      return { user: action.user, status: "authed" };
    case "CLEAR":
      return { user: null, status: "anon" };
    default:
      return state;
  }
}

// ── Context ────────────────────────────────────────────────────────

interface AuthContextValue extends AuthState {
  setSession: (accessToken: string, user: CurrentUser) => void;
  clear: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

// ── Provider ───────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  function setSession(accessToken: string, user: CurrentUser) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    dispatch({ type: "SET_SESSION", user });
  }

  function clear() {
    localStorage.removeItem(TOKEN_KEY);
    dispatch({ type: "CLEAR" });
  }

  return (
    <AuthContext.Provider value={{ ...state, setSession, clear }}>
      {children}
    </AuthContext.Provider>
  );
}

// ── Hook ───────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

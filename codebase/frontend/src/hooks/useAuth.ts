/**
 * useAuth.ts — auth ACTIONS hook, wrapping the API + AuthContext.
 *
 * Exported as `useAuthActions()` to avoid colliding with `useAuth()` in store/AuthContext,
 * which owns the session STATE (user, status). Components read state from AuthContext and
 * call side-effecting flows from here.
 *
 * EXPOSES:
 *   login(email, password)     -> LoginResult ({ mfaRequired, mfaSetupRequired, tempToken? })
 *   verifyMfa(tempToken, code) -> establishes a full session (token + user)
 *   setupMfa()                 -> MfaSetupResult (QR + otpauth uri)
 *   confirmMfa(code)           -> activates TOTP, refreshes user
 *   changePassword(cur, next)  -> changes password, refreshes user (clears isFirstLogin)
 *   logout()                   -> best-effort server logout + clears session
 *   bootstrap()                -> on app load, restore `user` from GET /users/me if a token exists
 *
 * All calls go through lib/apiClient (which attaches the token). No refresh flow in the
 * prototype — a 401 on an authed endpoint simply logs the user out (handled in apiClient).
 */

import { apiFetch } from "../lib/apiClient";
import { TOKEN_KEY, useAuth } from "../store/AuthContext";
import type { CurrentUser, LoginResult, MfaSetupResult } from "../types";

interface MeDto {
  id: string;
  email: string;
  full_name: string;
  role: CurrentUser["role"];
  mfa_enabled: boolean;
  is_first_login: boolean;
}

interface LoginDto {
  mfa_required?: boolean;
  temp_token?: string;
  access_token?: string;
  mfa_setup_required?: boolean;
}

function toCurrentUser(dto: MeDto): CurrentUser {
  return {
    id: dto.id,
    email: dto.email,
    fullName: dto.full_name,
    role: dto.role,
    mfaEnabled: dto.mfa_enabled,
    isFirstLogin: dto.is_first_login,
  };
}

export function useAuthActions() {
  const { setSession, setUser, clear } = useAuth();

  async function fetchMe(): Promise<CurrentUser> {
    return toCurrentUser((await apiFetch("/users/me")) as MeDto);
  }

  /** Stash the token (so apiFetch attaches it), load the profile, then commit to state. */
  async function establishSession(accessToken: string): Promise<CurrentUser> {
    localStorage.setItem(TOKEN_KEY, accessToken);
    const me = await fetchMe();
    setSession(accessToken, me);
    return me;
  }

  async function login(email: string, password: string): Promise<LoginResult> {
    const res = (await apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    })) as LoginDto;

    if (res.mfa_required && res.temp_token) {
      return { mfaRequired: true, mfaSetupRequired: false, tempToken: res.temp_token };
    }
    if (res.access_token) {
      await establishSession(res.access_token);
      return { mfaRequired: false, mfaSetupRequired: Boolean(res.mfa_setup_required) };
    }
    throw new Error("Unexpected login response");
  }

  async function verifyMfa(tempToken: string, code: string): Promise<void> {
    const res = (await apiFetch("/auth/mfa/verify", {
      method: "POST",
      body: JSON.stringify({ temp_token: tempToken, totp_code: code }),
    })) as { access_token: string };
    await establishSession(res.access_token);
  }

  async function setupMfa(): Promise<MfaSetupResult> {
    const res = (await apiFetch("/auth/mfa/setup")) as {
      otpauth_uri: string;
      qr_code_base64: string;
    };
    return { otpauthUri: res.otpauth_uri, qrCodeBase64: res.qr_code_base64 };
  }

  async function confirmMfa(code: string): Promise<void> {
    await apiFetch("/auth/mfa/confirm", {
      method: "POST",
      body: JSON.stringify({ totp_code: code }),
    });
    setUser(await fetchMe());
  }

  async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await apiFetch("/users/me/change-password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
    setUser(await fetchMe());
  }

  async function logout(): Promise<void> {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } catch {
      // Stateless JWT — a failed server call still means the client discards its token.
    }
    clear();
  }

  async function bootstrap(): Promise<void> {
    if (!localStorage.getItem(TOKEN_KEY)) {
      clear();
      return;
    }
    try {
      setUser(await fetchMe());
    } catch {
      clear();
    }
  }

  return { login, verifyMfa, setupMfa, confirmMfa, changePassword, logout, bootstrap };
}

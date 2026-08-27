/**
 * apiClient.ts — the single fetch wrapper every API call goes through.
 * Replaces the Axios instance. See CHANGES.md §5.
 *
 * RESPONSIBILITIES (prototype):
 *   - Base path "/api/v1" (Vite proxies this to the Flask backend in dev).
 *   - Attach Authorization: Bearer <token> from localStorage on every request.
 *   - On 401: clear the token and redirect to /login.
 *   - On non-OK response: throw with the API error message.
 *   - Never log request/response bodies (may contain PII).
 *
 * WHY NOT AXIOS:
 *   The deck removed Axios from the tech strip (CHANGES.md §5). Native fetch is
 *   sufficient for the prototype. IMPORTANT: fetch only rejects on network failure,
 *   never on 4xx/5xx — the explicit res.ok check below is what Axios gave for free.
 *
 * STEP-UP MFA:
 *   If the server returns 401 with { code: "MFA_REQUIRED" }, the caller should redirect
 *   to a step-up prompt rather than the login page. TODO: wire this up once the
 *   step-up flow is implemented (see feature_plans/auth_plan.md §Step-up MFA).
 *
 * PROTOTYPE SIMPLIFICATION:
 *   No silent token-refresh/retry logic — there's no refresh token yet (access token is
 *   long-lived). Production adds a refresh interceptor — auth_plan.md.
 *
 * EXPORTS: apiFetch
 */

const TOKEN_KEY = "dms_access_token";
const BASE = "/api/v1";

export async function apiFetch(path: string, init: RequestInit = {}): Promise<unknown> {
  const token = localStorage.getItem(TOKEN_KEY);

  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body && !(init.body instanceof FormData)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });

  if (res.status === 401) {
    // TODO: inspect res.json().code — if "MFA_REQUIRED", redirect to step-up, not login.
    localStorage.removeItem(TOKEN_KEY);
    if (location.pathname !== "/login") location.assign("/login");
    throw new Error("unauthorised");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: { message?: string } })?.error?.message ?? res.statusText);
  }

  return res.status === 204 ? null : res.json();
}

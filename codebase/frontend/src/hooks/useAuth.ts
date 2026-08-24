/**
 * useAuth.ts — auth actions hook, wrapping the API + authStore.
 *
 * EXPOSES (prototype):
 *   login(email, password)    -> { mfaRequired?, mfaSetupRequired?, tempToken? }
 *   verifyMfa(tempToken, code)-> sets session (token + user)
 *   setupMfa() / confirmMfa(code)
 *   changePassword(current, next)
 *   logout()                  -> clears session (no server refresh token to revoke)
 *   bootstrap()               -> on app load, if a token exists in the store, fetch
 *                                GET /users/me to restore `user`; set status accordingly.
 *
 * All calls go through lib/apiClient (which attaches the token). No refresh flow in the
 * prototype — a 401 simply logs the user out. See auth_plan.md for the production version.
 */

// TODO: implement using `api` from ../lib/apiClient and useAuthStore.
export function useAuth() {
  // return { login, verifyMfa, setupMfa, confirmMfa, changePassword, logout, bootstrap };
  throw new Error("TODO: implement useAuth");
}

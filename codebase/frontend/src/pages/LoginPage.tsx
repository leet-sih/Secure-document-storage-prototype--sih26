/**
 * LoginPage.tsx — /login  (public)
 *
 * FLOW:
 *   1. Email + password -> useAuth.login().
 *   2. If response.mfaRequired -> render the 6-digit code step -> useAuth.verifyMfa().
 *   3. If response.mfaSetupRequired -> redirect to /mfa-setup.
 *   4. On success -> redirect to / (or /change-password if isFirstLogin).
 *
 * UX: generic error text on failure ("Invalid credentials") — never reveal which field.
 * Show a locked-out message on 423. Disable submit while pending.
 */

export default function LoginPage() {
  // TODO: local state for step ("credentials" | "mfa"), form fields, error, loading.
  return null; // TODO: render the two-step form.
}

"""
auth_service.py — login, MFA, and session issuance logic.

FUNCTIONS (see auth_plan.md for full flows):
    authenticate(email, password) -> user | raises 401/423
        Verifies bcrypt hash; tracks failed_logins; locks after threshold.
    begin_session(user) -> dict
        If MFA set up: return {mfa_required, temp_token}. Else issue tokens +
        {mfa_setup_required: True}.
    complete_mfa(temp_token, totp_code) -> (user, access_token, refresh_token)
    setup_mfa(user) -> {otpauth_uri, qr_code_base64}     (stores pending secret)
    confirm_mfa(user, totp_code) -> None                  (activates pending secret)
    refresh(user_id, presented_refresh) -> (access_token, new_refresh) | raises 401
    logout(user_id, presented_refresh) -> None

RETURNS tokens; the blueprint sets the refresh cookie and records audit events.
"""


def authenticate(email: str, password: str):
    raise NotImplementedError


def begin_session(user) -> dict:
    raise NotImplementedError


def complete_mfa(temp_token: str, totp_code: str):
    raise NotImplementedError


def setup_mfa(user) -> dict:
    raise NotImplementedError


def confirm_mfa(user, totp_code: str) -> None:
    raise NotImplementedError


def refresh(user_id: str, presented_refresh: str):
    raise NotImplementedError


def logout(user_id: str, presented_refresh: str) -> None:
    raise NotImplementedError

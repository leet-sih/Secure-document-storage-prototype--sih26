"""
auth.py — authentication routes. Prefix: /api/v1/auth

ROUTES:
    POST /login          (public, rate-limited)  email+password -> {mfa_required,temp_token}
                                                  or {access_token, mfa_setup_required}
    POST /mfa/verify     (public, rate-limited)  temp_token+totp -> access_token (+refresh cookie)
    GET  /mfa/setup      (auth)                  -> {otpauth_uri, qr_code_base64}
    POST /mfa/confirm    (auth)                  totp_code -> activates MFA
    POST /refresh        (cookie only)           -> new access_token (+rotated refresh cookie)
    POST /logout         (auth)                  invalidate refresh token

Sets refresh_token as httpOnly, Secure, SameSite=Strict cookie. Records LOGIN / LOGIN_FAILED /
MFA_* / TOKEN_REFRESHED / LOGOUT audit events. See auth_plan.md.
"""

from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

# TODO: implement routes above.
# from app.extensions import limiter
# from app.core.rate_limit import LOGIN_LIMITS, MFA_LIMITS, REFRESH_LIMITS
# from app.schemas.auth_schemas import LoginSchema, MFAVerifySchema, MFAConfirmSchema
# from app.services import auth_service

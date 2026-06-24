"""Authentication: Google Identity Services + a signed session cookie (Slice 6).

Flow (prod, AUTH_MODE=google):
    1. The browser renders Google's "Sign in with Google" button (client-side GIS).
    2. On success GIS hands the page an ID token (a JWT), POSTed to /api/v1/auth/google.
    3. `verify_google_credential` validates the token's signature + audience against the
       configured GOOGLE_CLIENT_ID and returns the verified email.
    4. The email is checked against the allowlist (the admin is always allowed); on success
       we store {"email": ...} in the signed session cookie (Starlette SessionMiddleware).

Local/tests (AUTH_MODE=dev): there is no Google client, so /api/v1/auth/dev accepts an email
directly (still allowlist-gated) — letting the gate be exercised without real OAuth. That
endpoint refuses to run unless AUTH_MODE=="dev", so it can never weaken a prod deployment.

The gate itself is two FastAPI dependencies — `require_user` (any allowed account) and
`require_admin` (only ADMIN_EMAIL) — applied to the protected routes in main.py.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from .config import Settings, get_settings
from .models import SessionUser
from .users import get_user_repository

_SESSION_KEY = "email"


class AuthError(Exception):
    """Raised when a Google credential cannot be verified."""


def is_admin(email: str, settings: Settings | None = None) -> bool:
    """True if `email` is the configured bootstrap owner."""
    settings = settings or get_settings()
    return email.strip().lower() == settings.admin_email


def is_access_allowed(email: str, settings: Settings | None = None) -> bool:
    """True if `email` may use the app: the admin, or anyone on the allowlist."""
    settings = settings or get_settings()
    email = email.strip().lower()
    if is_admin(email, settings):
        return True
    return get_user_repository(settings).is_allowed(email)


def verify_google_credential(credential: str, settings: Settings | None = None) -> str:
    """Verify a Google ID token and return its (verified) email. Raises AuthError otherwise.

    Uses google-auth to check the JWT signature against Google's public certs and the
    audience against GOOGLE_CLIENT_ID. We additionally require a verified email claim.
    """
    settings = settings or get_settings()
    if not settings.google_client_id:
        raise AuthError("Google sign-in is not configured (GOOGLE_CLIENT_ID unset).")

    # Imported lazily so dev/test runs (and the import graph) don't require google-auth's
    # transport stack unless Google sign-in is actually used.
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(
            credential, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:  # bad signature / wrong audience / expired
        raise AuthError(f"Invalid Google credential: {exc}") from exc

    email = (claims.get("email") or "").strip().lower()
    if not email or not claims.get("email_verified"):
        raise AuthError("Google account has no verified email.")
    return email


# --- session helpers --------------------------------------------------------

def login_session(request: Request, email: str) -> None:
    """Record the signed-in email in the session cookie."""
    request.session[_SESSION_KEY] = email.strip().lower()


def logout_session(request: Request) -> None:
    """Clear the session cookie."""
    request.session.pop(_SESSION_KEY, None)


def current_user(request: Request) -> SessionUser | None:
    """Resolve the session into a SessionUser, or None if not signed in."""
    email = request.session.get(_SESSION_KEY)
    if not email:
        return None
    return SessionUser(email=email, is_admin=is_admin(email))


# --- FastAPI dependencies ---------------------------------------------------

def require_user(request: Request) -> SessionUser:
    """Gate: any signed-in, still-allowed account. 401 otherwise.

    Re-checks the allowlist on every request so revoking access takes effect immediately
    (a stale cookie can't outlive an admin's removal).
    """
    user = current_user(request)
    if user is None or not is_access_allowed(user.email):
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def require_admin(user: SessionUser = Depends(require_user)) -> SessionUser:
    """Gate: the bootstrap owner only. 403 for any other signed-in user."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user

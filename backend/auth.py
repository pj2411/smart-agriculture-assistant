"""Minimal Supabase Auth bearer verification for the FastAPI service.

The backend verifies the access token with Supabase Auth instead of decoding
JWTs itself. This works with projects using either current signing keys or the
legacy shared-secret configuration, and keeps the service-role key out of the
request path.
"""

import json
import os
from typing import Any, Dict, Optional
from urllib import error, request

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


bearer = HTTPBearer(auto_error=False)
DEMO_TOKEN = "jalsaathi-local-demo-farmer"


def _supabase_url() -> str:
    return (os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL") or "").strip().rstrip("/")


def _publishable_key() -> str:
    return (os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or "").strip()


def auth_status() -> Dict[str, Any]:
    return {
        "provider": "supabase",
        "configured": bool(_supabase_url() and _publishable_key()),
        "mode": "bearer_token_verified_by_supabase_auth",
        "local_demo_enabled": os.getenv("JALSAATHI_LOCAL_DEMO_AUTH", "false").lower() == "true",
    }


def require_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> Dict[str, Any]:
    """Require a valid Supabase access token and return the minimal user object."""
    demo_enabled = os.getenv("JALSAATHI_LOCAL_DEMO_AUTH", "false").lower() == "true"
    if demo_enabled and credentials and credentials.scheme.lower() == "bearer" and credentials.credentials == DEMO_TOKEN:
        return {"id": "local-demo-farmer", "email": "farmer@jalsaathi.local", "role": "demo_farmer", "demo": True}
    project_url = _supabase_url()
    publishable_key = _publishable_key()
    if not project_url or not publishable_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"category": "auth_not_configured", "message": "Supabase authentication is not configured on the server."},
        )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in is required.", headers={"WWW-Authenticate": "Bearer"})

    req = request.Request(
        f"{project_url}/auth/v1/user",
        headers={"apikey": publishable_key, "Authorization": f"Bearer {credentials.credentials}"},
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase session is not valid.")
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPException:
        raise
    except error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase session is not valid.", headers={"WWW-Authenticate": "Bearer"}) from exc
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"category": "auth_provider_error", "message": "Supabase Auth could not validate the session."}) from exc
    except error.URLError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"category": "auth_network_error", "message": "Supabase Auth could not be reached."}) from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"category": "auth_invalid_response", "message": "Supabase Auth returned an invalid response."}) from exc

    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase session did not contain a user.")
    return {"id": user_id, "email": payload.get("email"), "role": payload.get("role", "authenticated")}

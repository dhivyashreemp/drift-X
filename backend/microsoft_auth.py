import os
from urllib.parse import urlencode
import httpx

TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv(
    "MICROSOFT_REDIRECT_URI",
    "http://localhost:8000/api/auth/microsoft/callback",
)

_AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
_SCOPES = "openid email profile User.Read"


def is_configured() -> bool:
    return bool(CLIENT_ID and CLIENT_SECRET)


def get_auth_url() -> str:
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": _SCOPES,
        "response_mode": "query",
        "prompt": "select_account",
    }
    return f"{_AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_AUTHORITY}/oauth2/v2.0/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": REDIRECT_URI,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


async def get_ms_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

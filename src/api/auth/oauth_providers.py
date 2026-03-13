"""
OAuth2 provider integrations for Google, GitHub, and Apple sign-in.
"""
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from src.core.config import settings


@dataclass
class OAuthUserInfo:
    email: str
    provider: str
    provider_id: str


# ── Provider Configurations ──

_PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": "openid email profile",
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "emails_url": "https://api.github.com/user/emails",
        "scopes": "read:user user:email",
    },
    "apple": {
        "auth_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "scopes": "name email",
    },
}


def _get_client_credentials(provider: str) -> tuple[str, str]:
    """Return (client_id, client_secret) for a provider."""
    if provider == "google":
        return settings.google_client_id, settings.google_client_secret
    elif provider == "github":
        return settings.github_client_id, settings.github_client_secret
    elif provider == "apple":
        return settings.apple_client_id, settings.apple_client_secret
    raise ValueError(f"Unknown OAuth provider: {provider}")


def get_authorization_url(provider: str, state: str) -> str:
    """Build the OAuth authorization redirect URL."""
    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown OAuth provider: {provider}")

    cfg = _PROVIDERS[provider]
    client_id, _ = _get_client_credentials(provider)
    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/auth/{provider}/callback"

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": cfg["scopes"],
        "state": state,
    }

    if provider == "apple":
        params["response_mode"] = "form_post"

    return f"{cfg['auth_url']}?{urlencode(params)}"


async def exchange_code(provider: str, code: str) -> str:
    """Exchange an authorization code for an access token."""
    if provider not in _PROVIDERS:
        raise ValueError(f"Unknown OAuth provider: {provider}")

    cfg = _PROVIDERS[provider]
    client_id, client_secret = _get_client_credentials(provider)
    redirect_uri = f"{settings.oauth_redirect_base_url}/api/v1/auth/{provider}/callback"

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(cfg["token_url"], data=data, headers=headers)
        resp.raise_for_status()
        body = resp.json()

    return body["access_token"]


async def get_user_info(provider: str, access_token: str) -> OAuthUserInfo:
    """Fetch user email and provider ID from the OAuth provider."""
    async with httpx.AsyncClient() as client:
        if provider == "google":
            resp = await client.get(
                _PROVIDERS["google"]["userinfo_url"],
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return OAuthUserInfo(
                email=data["email"],
                provider="google",
                provider_id=str(data["id"]),
            )

        elif provider == "github":
            headers = {"Authorization": f"Bearer {access_token}"}
            # Get user profile
            resp = await client.get(_PROVIDERS["github"]["userinfo_url"], headers=headers)
            resp.raise_for_status()
            profile = resp.json()
            provider_id = str(profile["id"])

            # Email may be private — fetch from emails endpoint
            email = profile.get("email")
            if not email:
                resp = await client.get(_PROVIDERS["github"]["emails_url"], headers=headers)
                resp.raise_for_status()
                emails = resp.json()
                primary = next((e for e in emails if e.get("primary")), emails[0])
                email = primary["email"]

            return OAuthUserInfo(
                email=email,
                provider="github",
                provider_id=provider_id,
            )

        elif provider == "apple":
            # Apple sends user info in the id_token (JWT) during the first sign-in.
            # For subsequent sign-ins, we decode the id_token.
            import json
            import base64

            # Decode JWT payload without verification (Apple's public keys verify separately)
            parts = access_token.split(".")
            if len(parts) >= 2:
                payload = parts[1]
                # Add padding
                payload += "=" * (4 - len(payload) % 4)
                decoded = json.loads(base64.urlsafe_b64decode(payload))
                return OAuthUserInfo(
                    email=decoded.get("email", ""),
                    provider="apple",
                    provider_id=decoded.get("sub", ""),
                )
            raise ValueError("Invalid Apple id_token format")

    raise ValueError(f"Unknown OAuth provider: {provider}")

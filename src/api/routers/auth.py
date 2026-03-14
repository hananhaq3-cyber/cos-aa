"""
Authentication endpoints: login, register, OAuth, and user info.
"""
import secrets
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from src.api.auth.jwt_handler import TokenClaims, create_access_token, decode_access_token
from src.api.auth.password import hash_password, verify_password
from src.api.auth.oauth_providers import (
    exchange_code,
    get_authorization_url,
    get_user_info,
)
from src.api.schemas.auth_schemas import AuthResponse, LoginRequest, RegisterRequest
from src.core.config import settings
from src.db.models.tenant import Tenant
from src.db.models.user import User
from src.db.postgres import get_session

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _build_auth_response(
    user_id: UUID, tenant_id: UUID, email: str, role: str
) -> AuthResponse:
    token = create_access_token(
        user_id=user_id, tenant_id=tenant_id, role=role, scopes=[]
    )
    return AuthResponse(
        access_token=token,
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
        role=role,
        expires_in=settings.jwt_expire_minutes * 60,
    )


# ── Email / Password ──


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Authenticate with email and password."""
    try:
        async with get_session(tenant_id=None) as session:
            result = await session.execute(
                select(User).where(User.email == body.email)
            )
            user = result.scalar_one_or_none()

        if not user or not user.hashed_password:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(body.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        return _build_auth_response(user.id, user.tenant_id, user.email, user.role)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest):
    """Create a new tenant and user account."""
    try:
        async with get_session(tenant_id=None) as session:
            # Check if email already exists
            existing = await session.execute(
                select(User).where(User.email == body.email)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Email already registered")

            # Check if tenant name already exists
            existing_tenant = await session.execute(
                select(Tenant).where(Tenant.name == body.tenant_name)
            )
            if existing_tenant.scalar_one_or_none():
                raise HTTPException(status_code=409, detail="Organization name already taken")

            # Create tenant
            tenant = Tenant(
                name=body.tenant_name,
                quotas={
                    "max_sessions_per_day": 1000,
                    "max_llm_tokens_per_day": 5000000,
                    "max_agents": 20,
                    "max_concurrent_tasks": 50,
                },
            )
            session.add(tenant)
            await session.flush()

            # Create user as admin of new tenant
            user = User(
                tenant_id=tenant.id,
                email=body.email,
                hashed_password=hash_password(body.password),
                role="admin",
            )
            session.add(user)
            await session.flush()

        return _build_auth_response(user.id, tenant.id, user.email, user.role)
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Register error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


# ── OAuth ──


@router.get("/{provider}")
async def oauth_redirect(provider: str):
    """Redirect user to OAuth provider consent screen."""
    if provider not in ("google", "github", "apple"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    state = secrets.token_urlsafe(32)
    url = get_authorization_url(provider, state)
    return RedirectResponse(url=url)


@router.get("/{provider}/callback")
async def oauth_callback(provider: str, code: str, state: str | None = None):
    """Handle OAuth callback — exchange code, find/create user, redirect with token."""
    if provider not in ("google", "github", "apple"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    try:
        access_token = await exchange_code(provider, code)
        user_info = await get_user_info(provider, access_token)
    except Exception:
        raise HTTPException(status_code=400, detail="OAuth authentication failed")

    async with get_session(tenant_id=None) as session:
        # Look for existing user by OAuth provider ID
        result = await session.execute(
            select(User).where(
                User.oauth_provider == provider,
                User.oauth_provider_id == user_info.provider_id,
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            # Look for existing user by email
            result = await session.execute(
                select(User).where(User.email == user_info.email)
            )
            user = result.scalar_one_or_none()

            if user:
                # Link OAuth to existing account
                user.oauth_provider = provider
                user.oauth_provider_id = user_info.provider_id
                await session.flush()
            else:
                # Create new tenant + user
                tenant = Tenant(
                    name=f"{user_info.email.split('@')[0]}-org",
                    quotas={
                        "max_sessions_per_day": 1000,
                        "max_llm_tokens_per_day": 5000000,
                        "max_agents": 20,
                        "max_concurrent_tasks": 50,
                    },
                )
                session.add(tenant)
                await session.flush()

                user = User(
                    tenant_id=tenant.id,
                    email=user_info.email,
                    role="admin",
                    oauth_provider=provider,
                    oauth_provider_id=user_info.provider_id,
                )
                session.add(user)
                await session.flush()

    token = create_access_token(
        user_id=user.id, tenant_id=user.tenant_id, role=user.role, scopes=[]
    )

    # Redirect to frontend with token in query param
    frontend_url = settings.oauth_redirect_base_url or ""
    return RedirectResponse(url=f"{frontend_url}/login?token={token}")


# ── User Info ──


@router.get("/me")
async def get_me(request: Request):
    """Return current authenticated user info. Requires valid JWT."""
    claims: TokenClaims = request.state.claims
    async with get_session(tenant_id=claims.tenant_id) as session:
        result = await session.execute(
            select(User).where(User.id == claims.sub)
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "user_id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "email": user.email,
        "role": user.role,
    }

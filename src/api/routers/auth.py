"""
Authentication endpoints: login, register, OAuth, and user info.
"""
import secrets
from uuid import UUID
from datetime import datetime, timezone

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
from src.api.auth.token_blacklist import revoke_token
from src.api.auth.audit import log_audit_event
from src.api.auth.verification import (
    create_verification_token,
    validate_verification_token,
    check_resend_cooldown,
    set_resend_cooldown,
)
from src.api.auth.email import send_verification_email
from src.api.schemas.auth_schemas import (
    AuthResponse, LoginRequest, RegisterRequest, SessionResponse,
)
from src.core.config import settings
from src.db.models.tenant import Tenant
from src.db.models.user import User
from src.db.models.session import UserSession
from src.db.postgres import get_session
from src.db.redis_client import redis_client

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _get_client_info(request: Request) -> tuple[str | None, str | None]:
    """Extract client IP and user agent from request."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip, user_agent


def _build_auth_response(
    user_id: UUID,
    tenant_id: UUID,
    email: str,
    role: str,
    email_verified: bool = False,
) -> AuthResponse:
    token = create_access_token(
        user_id=user_id, tenant_id=tenant_id, role=role, scopes=[],
        email=email, email_verified=email_verified,
    )
    # Decode to get JTI and expiry for session tracking
    claims = decode_access_token(token)

    return AuthResponse(
        access_token=token,
        user_id=user_id,
        tenant_id=tenant_id,
        email=email,
        role=role,
        expires_in=settings.jwt_expire_minutes * 60,
        jti=claims.jti,
        email_verified=email_verified,
    )


# ── Email / Password ──


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request):
    """Authenticate with email and password."""
    ip, user_agent = _get_client_info(request)
    try:
        async with get_session(tenant_id=None) as session:
            result = await session.execute(
                select(User).where(User.email == body.email)
            )
            user = result.scalar_one_or_none()

        if not user or not user.hashed_password:
            await log_audit_event(
                tenant_id=None,  # Unknown tenant
                user_id=None,
                action="failed_login",
                status="failure",
                ip_address=ip,
                user_agent=user_agent,
                details={"reason": "invalid_credentials"},
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")

        if not verify_password(body.password, user.hashed_password):
            await log_audit_event(
                tenant_id=user.tenant_id,
                user_id=user.id,
                action="failed_login",
                status="failure",
                ip_address=ip,
                user_agent=user_agent,
                details={"reason": "invalid_password"},
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")

        response = _build_auth_response(
            user.id, user.tenant_id, user.email, user.role,
            email_verified=user.email_verified,
        )

        # Track session in database
        response_claims = decode_access_token(response.access_token)
        async with get_session(tenant_id=None) as session:
            session.add(UserSession(
                user_id=user.id,
                tenant_id=user.tenant_id,
                jti=response_claims.jti,
                user_agent=user_agent,
                ip_address=ip,
                expires_at=response_claims.exp,
            ))
            await session.flush()

        # Log successful login
        await log_audit_event(
            tenant_id=user.tenant_id,
            user_id=user.id,
            action="login",
            status="success",
            ip_address=ip,
            user_agent=user_agent,
        )

        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/register", response_model=AuthResponse)
async def register(body: RegisterRequest, request: Request):
    """Create a new tenant and user account."""
    ip, user_agent = _get_client_info(request)
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

        response = _build_auth_response(user.id, tenant.id, user.email, user.role)

        # Send verification email (don't fail registration on email error)
        try:
            verify_token = await create_verification_token(user.id)
            await send_verification_email(user.email, verify_token)
        except Exception as e:
            print(f"Failed to send verification email: {e}")

        # Log successful registration
        await log_audit_event(
            tenant_id=tenant.id,
            user_id=user.id,
            action="register",
            status="success",
            ip_address=ip,
            user_agent=user_agent,
        )

        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Register error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


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
        "email_verified": user.email_verified,
    }


@router.get("/verify-email")
async def verify_email(token: str):
    """Verify email address using token from verification email."""
    user_id = await validate_verification_token(token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired verification link")

    async with get_session(tenant_id=None) as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if user.email_verified:
            return {"message": "Email already verified"}
        user.email_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        await session.flush()

    await log_audit_event(
        tenant_id=user.tenant_id, user_id=user.id,
        action="email_verified", status="success",
    )
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(request: Request):
    """Resend verification email. Requires authentication. 60s cooldown."""
    claims: TokenClaims = request.state.claims

    async with get_session(tenant_id=None) as session:
        result = await session.execute(select(User).where(User.id == claims.sub))
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    if await check_resend_cooldown(user.id):
        raise HTTPException(status_code=429, detail="Please wait 60 seconds before requesting another email")

    token = await create_verification_token(user.id)
    await send_verification_email(user.email, token)
    await set_resend_cooldown(user.id)

    return {"message": "Verification email sent"}


@router.post("/logout")
async def logout(request: Request):
    """Logout the current user and revoke their token."""
    claims: TokenClaims = request.state.claims
    ip, user_agent = _get_client_info(request)

    try:
        # Revoke the token by adding JTI to blacklist
        token_ttl = int((claims.exp - datetime.now(timezone.utc)).total_seconds())
        if token_ttl > 0:
            await revoke_token(claims.jti, token_ttl)

        # Mark session as revoked in database
        async with get_session(tenant_id=None) as session:
            result = await session.execute(
                select(UserSession).where(UserSession.jti == claims.jti)
            )
            user_session = result.scalar_one_or_none()
            if user_session:
                user_session.revoked_at = datetime.now(timezone.utc)
                await session.flush()

        # Log the logout event
        await log_audit_event(
            tenant_id=claims.tenant_id,
            user_id=claims.sub,
            action="logout",
            status="success",
            ip_address=ip,
            user_agent=user_agent,
        )

        return {"message": "Logged out successfully"}
    except Exception as e:
        print(f"❌ Logout error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


# ── Session Management ──


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(request: Request):
    """List all active sessions for the current user."""
    claims: TokenClaims = request.state.claims

    async with get_session(tenant_id=None) as session:
        result = await session.execute(
            select(UserSession)
            .where(
                UserSession.user_id == claims.sub,
                UserSession.expires_at > datetime.now(timezone.utc),
            )
            .order_by(UserSession.created_at.desc())
        )
        sessions = result.scalars().all()

    return [
        SessionResponse(
            id=s.id,
            jti=s.jti,
            user_agent=s.user_agent,
            ip_address=s.ip_address,
            country=s.country,
            created_at=s.created_at,
            expires_at=s.expires_at,
            last_activity_at=s.last_activity_at,
            is_current=(s.jti == claims.jti),
            is_revoked=(s.revoked_at is not None),
        )
        for s in sessions
    ]


@router.post("/sessions/{jti}/revoke")
async def revoke_session(jti: str, request: Request):
    """Revoke a specific session by its JTI."""
    claims: TokenClaims = request.state.claims
    ip, user_agent = _get_client_info(request)

    async with get_session(tenant_id=None) as session:
        result = await session.execute(
            select(UserSession).where(
                UserSession.jti == jti,
                UserSession.user_id == claims.sub,
            )
        )
        user_session = result.scalar_one_or_none()

    if not user_session:
        raise HTTPException(status_code=404, detail="Session not found")

    if user_session.revoked_at:
        return {"message": "Session already revoked"}

    # Blacklist the token in Redis
    token_ttl = int((user_session.expires_at - datetime.now(timezone.utc)).total_seconds())
    if token_ttl > 0:
        await revoke_token(jti, token_ttl)

    # Mark session as revoked in database
    async with get_session(tenant_id=None) as session:
        result = await session.execute(
            select(UserSession).where(UserSession.jti == jti)
        )
        s = result.scalar_one()
        s.revoked_at = datetime.now(timezone.utc)
        await session.flush()

    await log_audit_event(
        tenant_id=claims.tenant_id,
        user_id=claims.sub,
        action="session_revoke",
        status="success",
        ip_address=ip,
        user_agent=user_agent,
        details={"revoked_jti": jti},
    )

    return {"message": "Session revoked successfully"}


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(request: Request):
    """Revoke all sessions for the current user (except the current one)."""
    claims: TokenClaims = request.state.claims
    ip, user_agent = _get_client_info(request)

    async with get_session(tenant_id=None) as session:
        result = await session.execute(
            select(UserSession).where(
                UserSession.user_id == claims.sub,
                UserSession.revoked_at.is_(None),
                UserSession.expires_at > datetime.now(timezone.utc),
                UserSession.jti != claims.jti,  # Keep current session
            )
        )
        sessions_to_revoke = result.scalars().all()

        now = datetime.now(timezone.utc)
        revoked_count = 0
        for s in sessions_to_revoke:
            s.revoked_at = now
            token_ttl = int((s.expires_at - now).total_seconds())
            if token_ttl > 0:
                await revoke_token(s.jti, token_ttl)
            revoked_count += 1

        await session.flush()

    await log_audit_event(
        tenant_id=claims.tenant_id,
        user_id=claims.sub,
        action="revoke_all_sessions",
        status="success",
        ip_address=ip,
        user_agent=user_agent,
        details={"revoked_count": revoked_count},
    )

    return {"message": f"Revoked {revoked_count} session(s)"}


# ── OAuth (catch-all routes MUST be last to avoid shadowing /me, /sessions, etc.) ──


async def _check_oauth_rate_limit(ip: str | None, limit_per_minute: int = 10) -> tuple[bool, int]:
    """Check IP-based rate limit for OAuth endpoints. Returns (allowed, remaining)."""
    if not ip:
        ip = "unknown"

    window = int(__import__("time").time()) // 60
    key = f"oauth_ratelimit:{ip}:{window}"

    try:
        current = await redis_client.client.incr(key)
        if current == 1:
            await redis_client.client.expire(key, 65)  # 65 seconds to cover next window

        remaining = max(0, limit_per_minute - current)
        allowed = current <= limit_per_minute
        return allowed, remaining
    except Exception:
        # If Redis fails, allow the request (fail open)
        return True, limit_per_minute


@router.get("/{provider}")
async def oauth_redirect(provider: str, request: Request):
    """Redirect user to OAuth provider consent screen."""
    if provider not in ("google", "github", "apple"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    # Rate limit by IP
    ip, _ = _get_client_info(request)
    allowed, remaining = await _check_oauth_rate_limit(ip, limit_per_minute=5)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Too many OAuth requests.")

    state = secrets.token_urlsafe(32)
    # Store state in Redis with 10-minute TTL for CSRF validation
    await redis_client.client.setex(f"oauth_state:{state}", 600, provider)
    url = get_authorization_url(provider, state)
    return RedirectResponse(url=url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str, request: Request, code: str, state: str | None = None,
):
    """Handle OAuth callback — exchange code, find/create user, redirect with token."""
    if provider not in ("google", "github", "apple"):
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

    ip, user_agent = _get_client_info(request)
    frontend_url = settings.oauth_redirect_base_url or ""

    # Rate limit by IP for callback (more lenient than redirect endpoint)
    allowed, remaining = await _check_oauth_rate_limit(ip, limit_per_minute=10)
    if not allowed:
        await log_audit_event(
            tenant_id=None, user_id=None,
            action="oauth_login", status="failure",
            ip_address=ip, user_agent=user_agent,
            details={"provider": provider, "reason": "rate_limit_exceeded"},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_failed")

    # Validate OAuth state parameter (CSRF protection)
    if state:
        stored = await redis_client.client.get(f"oauth_state:{state}")
        if stored is None:
            await log_audit_event(
                tenant_id=None, user_id=None,
                action="oauth_login", status="failure",
                ip_address=ip, user_agent=user_agent,
                details={"provider": provider, "reason": "invalid_state"},
            )
            return RedirectResponse(url=f"{frontend_url}/login?error=invalid_state")
        # Delete state after use (one-time use)
        await redis_client.client.delete(f"oauth_state:{state}")

    try:
        token_response = await exchange_code(provider, code)
        user_info = await get_user_info(provider, token_response)
    except Exception as e:
        await log_audit_event(
            tenant_id=None, user_id=None,
            action="oauth_login", status="failure",
            ip_address=ip, user_agent=user_agent,
            details={"provider": provider, "reason": str(e)},
        )
        return RedirectResponse(url=f"{frontend_url}/login?error=oauth_failed")

    async with get_session(tenant_id=None) as session:
        # Look for existing user by OAuth provider ID
        result = await session.execute(
            select(User).where(
                User.oauth_provider == provider,
                User.oauth_provider_id == user_info.provider_id,
            )
        )
        user = result.scalar_one_or_none()

        if user and not user.email_verified:
            user.email_verified = True
            user.email_verified_at = datetime.now(timezone.utc)
            await session.flush()

        if not user:
            # Look for existing user by email
            result = await session.execute(
                select(User).where(User.email == user_info.email)
            )
            user = result.scalar_one_or_none()

            if user:
                # Account exists with same email but different provider
                # For security, don't auto-link. Instead, require explicit confirmation
                # For now, we'll prevent linking and return an error
                # (In production, you'd want a separate flow for account linking)

                # Check if it's the same provider (shouldn't happen, caught earlier)
                if user.oauth_provider == provider:
                    # Same provider, just verify email
                    if not user.email_verified:
                        user.email_verified = True
                        user.email_verified_at = datetime.now(timezone.utc)
                        await session.flush()
                else:
                    # Different provider - account linking would be unsafe without explicit user consent
                    # For now, we reject this and tell user to use their original provider
                    await log_audit_event(
                        tenant_id=user.tenant_id, user_id=user.id,
                        action="oauth_login", status="failure",
                        ip_address=ip, user_agent=user_agent,
                        details={"provider": provider, "reason": "account_exists_different_provider"},
                    )
                    return RedirectResponse(
                        url=f"{frontend_url}/login?error=account_exists_with_different_provider"
                    )
            else:
                # Create new tenant + user
                # Use email hash to avoid name collisions
                import hashlib
                email_hash = hashlib.sha256(user_info.email.encode()).hexdigest()[:8]
                tenant = Tenant(
                    name=f"tenant-{email_hash}",
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
                    email_verified=True,
                    email_verified_at=datetime.now(timezone.utc),
                )
                session.add(user)
                await session.flush()

    token = create_access_token(
        user_id=user.id, tenant_id=user.tenant_id, role=user.role, scopes=[],
        email=user.email, email_verified=user.email_verified,
    )

    # Track session in database
    token_claims = decode_access_token(token)
    async with get_session(tenant_id=None) as session:
        session.add(UserSession(
            user_id=user.id,
            tenant_id=user.tenant_id,
            jti=token_claims.jti,
            user_agent=user_agent,
            ip_address=ip,
            expires_at=token_claims.exp,
        ))
        await session.flush()

    # Log successful OAuth login
    await log_audit_event(
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="oauth_login",
        status="success",
        ip_address=ip,
        user_agent=user_agent,
        details={"provider": provider},
    )

    # Redirect to frontend with token in secure HTTP-only cookie (not URL)
    response = RedirectResponse(url=f"{frontend_url}/login", status_code=302)
    response.set_cookie(
        key="__auth",
        value=token,
        max_age=3600,  # 60 minutes (same as token expiry)
        httponly=True,
        secure=True,  # HTTPS only in production
        samesite="lax",
        path="/",
    )
    return response

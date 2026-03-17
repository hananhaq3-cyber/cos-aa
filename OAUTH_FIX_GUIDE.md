# OAuth Configuration Fix Guide

## Problem
OAuth login was failing with **"Error 400: invalid_request"** because the redirect URLs were misconfigured.

## Root Cause
The `oauth_redirect_base_url` was pointing to the **frontend** (`http://localhost:5173`) instead of the **backend** where the OAuth callback endpoints are located.

## Code Fixes Applied ✅

### 1. Fixed `src/core/config.py` (line 57)
```python
# BEFORE (WRONG):
oauth_redirect_base_url: str = "http://localhost:5173"

# AFTER (CORRECT):
oauth_redirect_base_url: str = "http://localhost:8000"  # Backend URL for OAuth callbacks
```

### 2. Fixed `src/api/routers/auth.py` (line 507)
```python
# BEFORE (WRONG):
frontend_url = settings.oauth_redirect_base_url or ""

# AFTER (CORRECT):
frontend_url = settings.frontend_url or "https://cos-aa.vercel.app"
```

## Railway Environment Variable Setup 🚀

**IMPORTANT**: You must set this environment variable in Railway:

1. Go to: https://railway.app/dashboard
2. Select your `cos-aa-production` project
3. Click on the backend service
4. Go to **Variables** tab
5. Add this variable:

```bash
OAUTH_REDIRECT_BASE_URL=https://cos-aa-production.up.railway.app
```

6. Click **Deploy** to restart the service with the new variable

## Google Cloud Console Setup 🔐

### Required Redirect URIs
Add these **Authorized redirect URIs** in Google Cloud Console:

1. Go to: https://console.cloud.google.com/apis/credentials
2. Select your OAuth 2.0 Client ID
3. Add these URIs under **Authorized redirect URIs**:

```
https://cos-aa-production.up.railway.app/api/v1/auth/google/callback
http://localhost:8000/api/v1/auth/google/callback
```

4. Click **Save**

### Authorized JavaScript Origins (Optional)
Add these for better CORS support:

```
https://cos-aa.vercel.app
https://cos-aa-production.up.railway.app
http://localhost:5173
http://localhost:8000
```

## GitHub OAuth Setup 🐙

1. Go to: https://github.com/settings/developers (or your GitHub App settings)
2. Select your OAuth App
3. Update **Authorization callback URL** to:

```
https://cos-aa-production.up.railway.app/api/v1/auth/github/callback
```

4. For local development, create a separate OAuth App with:
```
http://localhost:8000/api/v1/auth/github/callback
```

## Apple Sign In Setup 🍎

1. Go to: https://developer.apple.com/account/resources/identifiers/list/serviceId
2. Select your Service ID
3. Configure **Return URLs**:

```
https://cos-aa-production.up.railway.app/api/v1/auth/apple/callback
http://localhost:8000/api/v1/auth/apple/callback
```

4. Click **Save**

## Expected OAuth Flow

### Correct Flow:
1. User clicks "Sign in with Google" on: `https://cos-aa.vercel.app/login`
2. Frontend redirects to: `https://cos-aa-production.up.railway.app/api/v1/auth/google/redirect`
3. Backend redirects to: `https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=https://cos-aa-production.up.railway.app/api/v1/auth/google/callback`
4. User approves on Google
5. Google redirects back to: `https://cos-aa-production.up.railway.app/api/v1/auth/google/callback?code=...`
6. Backend exchanges code for token, creates user session
7. Backend sets HTTP-only cookie with JWT
8. Backend redirects to: `https://cos-aa.vercel.app/login` (frontend validates cookie via `/auth/me`)
9. User is logged in ✅

## Testing After Setup

### 1. Check Railway Logs
```bash
# After deploying, check logs for:
railway logs --environment production
```

Look for: `OAuth redirect base URL: https://cos-aa-production.up.railway.app`

### 2. Test OAuth Flow
1. Go to: https://cos-aa.vercel.app/login
2. Click "Sign in with Google"
3. Should redirect to Google sign-in
4. After approval, should redirect back and log you in
5. Check browser DevTools → Application → Cookies for `cos_aa_token`

### 3. Verify Redirect URI
Check the URL when redirected to Google - it should contain:
```
redirect_uri=https://cos-aa-production.up.railway.app/api/v1/auth/google/callback
```

## Troubleshooting

### Still getting "Error 400: invalid_request"?
- ✅ Check Railway has `OAUTH_REDIRECT_BASE_URL` environment variable set
- ✅ Check Google Cloud Console has correct redirect URI (exact match required)
- ✅ Check Railway deployment has finished (wait 2-3 minutes)
- ✅ Clear browser cache and try again

### "redirect_uri_mismatch" error?
- The URL in Google Cloud Console must **exactly match** the one being sent
- Check Railway logs to see what redirect_uri is being sent
- Make sure there are no trailing slashes or typos

### OAuth works locally but not in production?
- Make sure Railway environment variable is set
- Local uses `http://localhost:8000`, production uses `https://cos-aa-production.up.railway.app`
- Both need separate OAuth client configurations (or add both URIs to same client)

## Summary

✅ **Code Fixed**: `config.py` and `auth.py` updated
✅ **Pushed to GitHub**: Commit `17407ee`
🚀 **Next Step**: Set Railway environment variable `OAUTH_REDIRECT_BASE_URL`
🔐 **Then**: Update Google/GitHub/Apple OAuth redirect URIs
🎉 **Result**: OAuth login will work correctly

---

**Commit Hash**: `17407ee`
**Files Changed**: `src/core/config.py`, `src/api/routers/auth.py`
**Date**: 2026-03-17

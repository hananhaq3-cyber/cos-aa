# 🔧 OAuth Error Fixes - 100% Solution Guide

## Current Errors

### ❌ Error 1: Google OAuth - "Error 401: invalid_client"
**Cause**: The `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` in Railway doesn't match your Google Cloud Console credentials.

### ❌ Error 2: GitHub OAuth - 404 Page
**Cause**: No GitHub OAuth app created yet, or redirect URI mismatch.

### ❌ Error 3: Frontend "Network Error"
**Cause**: Missing Vercel environment variable or stale deployment.

---

## ✅ FIX 1: Google OAuth (401 Error)

### Step 1: Get Your CORRECT Google Credentials

1. Go to: **https://console.cloud.google.com/apis/credentials**
2. Find your OAuth client: **"COS-AA Production"**
3. Click on it to view details
4. **Copy the EXACT values**:
   - Client ID: `123456789...apps.googleusercontent.com`
   - Client secret: `GOCSPX-...`

### Step 2: Verify Redirect URIs in Google Console

Make sure these **EXACT** URIs are listed:
```
https://cos-aa-production.up.railway.app/api/v1/auth/google/callback
http://localhost:8000/api/v1/auth/google/callback
```

⚠️ **NO trailing slashes!** Must match exactly.

### Step 3: Update Railway Variables

1. Go to Railway dashboard → Your project → Variables tab
2. Find `GOOGLE_CLIENT_ID` - Click edit
3. **Delete the old value** and paste the exact Client ID from Google Console
4. Find `GOOGLE_CLIENT_SECRET` - Click edit
5. **Delete the old value** and paste the exact Client Secret from Google Console
6. Click **"Deploy"** or wait for auto-deploy (2-3 minutes)

### Step 4: Test Google OAuth

After Railway redeploys:
1. Go to: https://cos-aa.vercel.app/login
2. Click **"Sign in with Google"**
3. Should redirect to Google sign-in (NO ERROR!)
4. Sign in with your Google account
5. Should redirect back to the app logged in ✅

---

## ✅ FIX 2: GitHub OAuth (404 Error)

### Step 1: Create GitHub OAuth App

1. Go to: **https://github.com/settings/developers**
2. Click **"New OAuth App"** (green button)
3. Fill in:
   ```
   Application name: COS-AA Production
   Homepage URL: https://cos-aa.vercel.app
   Authorization callback URL: https://cos-aa-production.up.railway.app/api/v1/auth/github/callback
   ```
4. Click **"Register application"**

### Step 2: Get GitHub Credentials

1. After creating, you'll see **Client ID** (already visible)
2. Click **"Generate a new client secret"**
3. ⚠️ **Copy IMMEDIATELY** (it only shows once!)
   - Client ID: `Iv1.abc123...`
   - Client Secret: `ghp_...` or similar

### Step 3: Add to Railway Variables

1. Go to Railway → Variables tab
2. Add/Update these variables:
   ```
   GITHUB_CLIENT_ID=<paste-github-client-id>
   GITHUB_CLIENT_SECRET=<paste-github-client-secret>
   ```
3. Click **"Deploy"** (wait 2-3 minutes)

### Step 4: Test GitHub OAuth

1. Go to: https://cos-aa.vercel.app/login
2. Click **"Sign in with GitHub"**
3. Should redirect to GitHub sign-in (NO 404!)
4. Authorize the app
5. Should redirect back logged in ✅

---

## ✅ FIX 3: Frontend Network Error

### Option A: Set Vercel Environment Variable (Recommended)

1. Go to: **https://vercel.com/dashboard**
2. Select your **cos-aa** project
3. Go to **Settings** → **Environment Variables**
4. Add new variable:
   ```
   Key: VITE_API_URL
   Value: https://cos-aa-production.up.railway.app
   Environment: Production ✅ Preview ✅ Development ✅
   ```
5. Click **"Save"**
6. Go to **Deployments** tab
7. Click **"..."** on the latest deployment → **"Redeploy"**
8. Wait 1-2 minutes for redeployment

### Option B: Rebuild and Redeploy Frontend (Alternative)

If Option A doesn't work, redeploy manually:

```bash
cd cos-aa/frontend
npm run build
```

Then commit and push (Vercel will auto-deploy):
```bash
git add -A
git commit -m "Rebuild frontend with correct API URL"
git push origin main
```

### Verify Frontend Connection

1. Go to: https://cos-aa.vercel.app
2. Open DevTools → Console (F12)
3. Try logging in with email/password
4. Should show API calls to `https://cos-aa-production.up.railway.app/api/v1/...`
5. NO "Network Error" ✅

---

## 🎯 CHECKLIST: All Variables in Railway

Make sure Railway has **ALL** these variables:

```bash
✅ OAUTH_REDIRECT_BASE_URL=https://cos-aa-production.up.railway.app
✅ FRONTEND_URL=https://cos-aa.vercel.app
✅ GOOGLE_CLIENT_ID=<your-google-client-id>
✅ GOOGLE_CLIENT_SECRET=<your-google-client-secret>
✅ GITHUB_CLIENT_ID=<your-github-client-id>
✅ GITHUB_CLIENT_SECRET=<your-github-client-secret>
✅ APP_ENV=production
✅ DATABASE_URL=<railway-postgres-url>
✅ REDIS_URL=<railway-redis-url>
```

---

## 🧪 FINAL TESTING CHECKLIST

### Test 1: Email/Password Login ✅
1. Go to: https://cos-aa.vercel.app/login
2. Enter email and password
3. Click "Sign In"
4. Should log in successfully (NO network error)

### Test 2: Google OAuth ✅
1. Go to: https://cos-aa.vercel.app/login
2. Click "Sign in with Google"
3. Should redirect to Google (NO "invalid_client" error)
4. Sign in with Google account
5. Should redirect back logged in

### Test 3: GitHub OAuth ✅
1. Go to: https://cos-aa.vercel.app/login
2. Click "Sign in with GitHub"
3. Should redirect to GitHub (NO 404 error)
4. Authorize the app
5. Should redirect back logged in

### Test 4: Registration ✅
1. Go to: https://cos-aa.vercel.app/login
2. Click "Sign Up"
3. Fill in email, password, org name
4. Click "Create Account"
5. Should register successfully

---

## 🚨 COMMON MISTAKES TO AVOID

### ❌ Wrong Client ID/Secret
- **Problem**: Copy-pasted the wrong values or included extra spaces
- **Fix**: Go back to Google/GitHub console, copy again EXACTLY

### ❌ Redirect URI Mismatch
- **Problem**: URIs in Google/GitHub console don't match exactly
- **Fix**: Must be EXACT match (no trailing slash, correct protocol https://)

### ❌ Railway Variables Not Saved
- **Problem**: Added variables but didn't trigger redeploy
- **Fix**: After adding variables, Railway should auto-deploy. If not, manually trigger deploy.

### ❌ Vercel Using Old Build
- **Problem**: Vercel cached old frontend without API URL
- **Fix**: Redeploy from Vercel dashboard → Deployments → Redeploy

### ❌ Wrong Google Project
- **Problem**: Created OAuth client in wrong Google Cloud project
- **Fix**: Make sure you're in the correct project (check project name in top bar)

---

## 📊 HOW TO VERIFY FIXES WORKED

### Check Railway Logs (Backend)
```bash
# Should show:
✅ Redis connected
✅ Database initialized
✅ Application startup complete
```

### Check Vercel Logs (Frontend)
```bash
# Should show:
✅ Build succeeded
✅ VITE_API_URL=https://cos-aa-production.up.railway.app
```

### Check Browser Console (Frontend)
```javascript
// Should make requests to:
https://cos-aa-production.up.railway.app/api/v1/auth/login
// NOT:
/api/v1/auth/login (relative path = WRONG)
```

---

## ⏱️ EXPECTED TIMELINE

1. **Fix Railway Variables**: 5 minutes + 2-3 min deploy = ~8 minutes
2. **Fix Google OAuth**: 3 minutes + 2-3 min deploy = ~6 minutes
3. **Fix GitHub OAuth**: 5 minutes + 2-3 min deploy = ~8 minutes
4. **Fix Vercel Frontend**: 2 minutes + 1-2 min deploy = ~4 minutes

**Total:** ~25-30 minutes to fix everything

---

## 🆘 STILL NOT WORKING?

### Debug Steps:

1. **Check Railway is running**:
   ```bash
   curl https://cos-aa-production.up.railway.app/health
   # Should return: {"healthy":true,"checks":{"redis":true}}
   ```

2. **Check Google OAuth redirect**:
   ```bash
   curl -L "https://cos-aa-production.up.railway.app/api/v1/auth/google"
   # Should redirect to accounts.google.com (NOT show error page)
   ```

3. **Check Frontend API URL**:
   - Open https://cos-aa.vercel.app
   - DevTools → Network tab
   - Try logging in
   - Check request URL starts with `https://cos-aa-production.up.railway.app`

4. **Check Railway Environment Variables**:
   - Railway dashboard → Variables
   - Verify ALL 6 OAuth variables are set correctly
   - NO extra spaces, NO quotes around values

---

## ✅ SUCCESS CRITERIA

When everything is fixed:
- ✅ Google OAuth: Opens Google login page (no error)
- ✅ GitHub OAuth: Opens GitHub authorization page (no 404)
- ✅ Email login: Logs in successfully (no network error)
- ✅ All requests go to: `https://cos-aa-production.up.railway.app/api/v1/...`

---

**Follow this guide step by step. Do NOT skip steps. Each fix builds on the previous one.**

**🎯 Goal: 100% working OAuth + Email login in ~30 minutes**

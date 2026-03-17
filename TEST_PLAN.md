# Complete End-to-End Test Plan

## Backend Test
```bash
# Test signup via curl
curl -X POST https://cos-aa-production.up.railway.app/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123","tenant_name":"Test Org"}'

# Expected response: JSON with access_token, user_id, tenant_id
# Should NOT contain error message
```

## Frontend Test
1. Go to https://cos-aa.vercel.app
2. Hard refresh (Ctrl+Shift+R)
3. Try to sign up with:
   - Email: `newuser@example.com`
   - Password: `NewUserPass123`
   - Organization: `New Test Org`
4. Should see either:
   - ✅ Success message with token
   - 🔄 Redirected to dashboard (if signup succeeds)

## Network Debugging
If still getting 404 or CORS errors:
1. Open DevTools (F12)
2. Go to Network tab
3. Try signup again
4. Click the failed request
5. Check URL and Status Code

## Success Indicators
- ✅ Backend: /auth/register returns JWT token
- ✅ Frontend loads without 404 errors
- ✅ No CORS errors in console
- ✅ Signup form submits without errors

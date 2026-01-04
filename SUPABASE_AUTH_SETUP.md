# Supabase Auth Email Confirmation Setup Guide

This guide explains how to configure Supabase Auth for proper email confirmation redirects in both development and production environments.

## 📋 Prerequisites

- Supabase project created
- Frontend application deployed (for production)
- Environment variables configured

## 🔧 Supabase Dashboard Configuration

### Step 1: Configure Site URL

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Navigate to **Authentication** → **URL Configuration**
3. Set the **Site URL** based on your environment:

   **For Development:**
   ```
   http://localhost:5173
   ```
   (or your local dev port, e.g., `http://localhost:3000`)

   **For Production:**
   ```
   https://yourdomain.com
   ```
   (replace with your actual production domain)

### Step 2: Configure Redirect URLs

In the same **URL Configuration** section, add the following **Redirect URLs**:

**For Development:**
```
http://localhost:5173/auth/confirm
http://localhost:5173/**
```

**For Production:**
```
https://yourdomain.com/auth/confirm
https://yourdomain.com/**
```

**Important Notes:**
- The `/**` wildcard allows all paths under your domain
- The specific `/auth/confirm` path is required for email confirmation
- Add both development and production URLs if you need both environments

### Step 3: Email Templates (Optional)

1. Navigate to **Authentication** → **Email Templates**
2. Customize the **Confirm signup** template if needed
3. The confirmation link will automatically use your configured redirect URL

## 🌍 Environment Variables

### Frontend `.env` File

Create or update `frontend/.env`:

**For Development:**
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-anon-key
VITE_APP_URL=http://localhost:5173
```

**For Production:**
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-anon-key
VITE_APP_URL=https://yourdomain.com
```

**Note:** `VITE_APP_URL` is optional. If not set, the app will use `window.location.origin` as a fallback.

## 🔄 How It Works

### Signup Flow

1. User signs up → `AuthContext.signUp()` is called
2. Frontend sends signup request with `emailRedirectTo: ${VITE_APP_URL}/auth/confirm`
3. Supabase sends confirmation email with link containing tokens
4. User clicks link → Redirected to `/auth/confirm` page
5. `EmailConfirm` component processes tokens and creates session
6. User is redirected to `/dashboard` if successful

### Email Confirmation Flow

```
User clicks email link
    ↓
Redirected to: https://yourdomain.com/auth/confirm#access_token=...&refresh_token=...
    ↓
EmailConfirm component extracts tokens from URL hash
    ↓
Exchanges tokens for session via supabase.auth.setSession()
    ↓
Session created → User authenticated
    ↓
Redirected to /dashboard
```

## ✅ Verification Steps

### Test in Development

1. Start your dev server: `npm run dev`
2. Sign up with a test email
3. Check your email for confirmation link
4. Click the link
5. Should redirect to `http://localhost:5173/auth/confirm`
6. Then automatically redirect to `http://localhost:5173/dashboard`

### Test in Production

1. Deploy your frontend
2. Sign up with a test email
3. Check your email for confirmation link
4. Click the link
5. Should redirect to `https://yourdomain.com/auth/confirm`
6. Then automatically redirect to `https://yourdomain.com/dashboard`

## 🐛 Troubleshooting

### Issue: Redirects to localhost in production

**Solution:** 
- Check `VITE_APP_URL` in production `.env`
- Verify Supabase Site URL is set to production domain
- Clear browser cache and try again

### Issue: "Invalid confirmation link" error

**Solution:**
- Verify redirect URL is added in Supabase dashboard
- Check that `/auth/confirm` route exists in your app
- Ensure tokens are being extracted from URL hash correctly

### Issue: Email confirmation works but user not logged in

**Solution:**
- Check browser console for errors
- Verify `supabase.auth.setSession()` is being called
- Check that session is being stored in localStorage

### Issue: CORS errors

**Solution:**
- Ensure your production domain is added to Supabase allowed origins
- Check Supabase project settings → API → CORS configuration

## 📚 Best Practices

1. **Always use HTTPS in production** - Required for secure token transmission
2. **Separate environments** - Use different Supabase projects for dev/prod if possible
3. **Test email delivery** - Verify emails are not going to spam
4. **Monitor auth events** - Use Supabase dashboard to track signups and confirmations
5. **Handle edge cases** - The `EmailConfirm` component handles expired links, already-confirmed users, etc.

## 🔐 Security Notes

- Email confirmation tokens are single-use and time-limited
- Tokens are transmitted via URL hash (not query params) for security
- Never log or expose tokens in client-side code
- Always validate tokens server-side if you add backend verification

## 📝 Summary

**Required Supabase Settings:**
- ✅ Site URL: Your app's base URL
- ✅ Redirect URLs: Include `/auth/confirm` and `/**` wildcard

**Required Frontend:**
- ✅ `VITE_APP_URL` environment variable (optional, has fallback)
- ✅ `/auth/confirm` route with `EmailConfirm` component
- ✅ Updated `AuthContext` with proper `emailRedirectTo`

**Result:**
- ✅ Email confirmation links redirect to your app (not localhost)
- ✅ Works in both development and production
- ✅ Users automatically logged in after confirmation
- ✅ Proper error handling for edge cases


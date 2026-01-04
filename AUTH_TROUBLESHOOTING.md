# Authentication Troubleshooting Guide

## ✅ What Was Fixed

1. **Enhanced Error Handling**
   - Proper error conversion from Supabase errors to user-friendly messages
   - Better error logging for debugging
   - Handles edge cases and network errors

2. **Improved Sign-In Flow**
   - Email trimming to avoid whitespace issues
   - Better session state management
   - Proper navigation after successful login

3. **Supabase Configuration Validation**
   - Console warnings if environment variables are missing
   - Better error messages pointing to where to find API keys

4. **Robust Error Messages**
   - Maps technical errors to user-friendly messages
   - Handles common scenarios (invalid credentials, email not confirmed, etc.)

## 🔍 Verify Your Supabase Configuration

### Step 1: Check Your `.env` File

Your `frontend/.env` file should have:

```env
VITE_SUPABASE_URL=https://chstjobzliwzqxmipsqs.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-anon-key-here
```

### Step 2: Get Your Correct Anon Key

1. Go to https://app.supabase.com
2. Select your project: `chstjobzliwzqxmipsqs`
3. Navigate to **Settings** → **API**
4. Under **Project API keys**, copy the **`anon`** or **`public`** key
5. It should be a JWT token starting with `eyJ...`

### Step 3: Update `.env` File

Replace the `VITE_SUPABASE_PUBLISHABLE_KEY` value with your actual anon key.

### Step 4: Restart Dev Server

After updating `.env`:
```bash
# Stop the server (Ctrl+C)
# Then restart:
npm run dev
```

## 🐛 Common Issues & Solutions

### Issue: "Invalid API key" Error

**Solution:**
- Verify you're using the `anon` key (not `service_role`)
- Check the key starts with `eyJ...` (JWT format)
- Ensure no extra spaces or quotes in `.env`
- Restart dev server after changes

### Issue: "Login failed" with Correct Credentials

**Possible Causes:**
1. **Email not confirmed** - Check your email and click confirmation link
2. **Wrong Supabase project** - Verify URL matches your project
3. **API key mismatch** - Ensure key matches the project
4. **Network issues** - Check browser console for CORS errors

**Solution:**
- Check browser console (F12) for detailed error messages
- Verify email is confirmed in Supabase Dashboard → Authentication → Users
- Try signing up again with a new account

### Issue: "Email not confirmed" Error

**Solution:**
1. Check your email inbox (and spam folder)
2. Click the confirmation link in the email
3. If link expired, request a new confirmation email from Supabase Dashboard

### Issue: Session Not Persisting

**Solution:**
- Clear browser localStorage and try again
- Check that `persistSession: true` is set in Supabase client config
- Verify localStorage is enabled in your browser

## 📝 Testing Checklist

- [ ] `.env` file has correct `VITE_SUPABASE_URL`
- [ ] `.env` file has correct `VITE_SUPABASE_PUBLISHABLE_KEY` (anon key)
- [ ] Dev server restarted after `.env` changes
- [ ] Browser console shows no Supabase configuration errors
- [ ] Can sign up successfully
- [ ] Can sign in with confirmed account
- [ ] Session persists after page refresh
- [ ] Can sign out successfully

## 🔐 Security Notes

- ✅ Never commit `.env` file to git
- ✅ Never use `service_role` key in frontend code
- ✅ Always use `anon` key for client-side authentication
- ✅ Keep your Supabase keys secure

## 📞 Still Having Issues?

1. **Check Browser Console** (F12 → Console tab)
   - Look for Supabase errors
   - Check network requests to Supabase

2. **Check Supabase Dashboard**
   - Go to Authentication → Users
   - Verify user exists and email is confirmed
   - Check for any account restrictions

3. **Verify Network**
   - Check if Supabase URL is accessible
   - Verify no firewall/proxy blocking requests

4. **Test with Fresh Account**
   - Try signing up with a new email
   - Complete email confirmation
   - Then try logging in


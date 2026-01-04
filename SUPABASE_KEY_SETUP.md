# Supabase API Key Setup Guide

## 🎯 Which Key to Use?

Supabase has **two types of API keys** you can use:

### Option 1: New Publishable Key (Recommended) ✅
- **Location:** Settings → API → **"Publishable and secret API keys"** tab
- **Format:** Starts with `sb_publishable_...`
- **Example:** `sb_publishable_JUWbMQlBQsWAK10hRDIvnw_iP8b0DGU`
- **Status:** ✅ **This is the key you see in your screenshot!**

### Option 2: Legacy Anon Key (Alternative)
- **Location:** Settings → API → **"Legacy anon, service_role API keys"** tab
- **Format:** Starts with `eyJ...` (JWT token)
- **Example:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
- **Status:** Still works, but new format is preferred

## 📋 Step-by-Step Instructions

### Using the New Publishable Key (What You See)

1. **In Supabase Dashboard:**
   - You're already on the right page: **Settings → API**
   - You're on the **"Publishable and secret API keys"** tab ✅
   - Find the **"Publishable key"** section
   - Copy the key that starts with `sb_publishable_...`

2. **Update Your `.env` File:**
   ```env
   VITE_SUPABASE_URL=https://chstjobzliwzqxmipsqs.supabase.co
   VITE_SUPABASE_PUBLISHABLE_KEY=sb_publishable_JUWbMQlBQsWAK10hRDIvnw_iP8b0DGU
   ```
   ⚠️ **Important:** Copy the FULL key (not just the visible part)

3. **Restart Your Dev Server:**
   ```bash
   # Stop server (Ctrl+C)
   npm run dev
   ```

### Using Legacy Anon Key (Alternative)

If you prefer the legacy format:

1. **In Supabase Dashboard:**
   - Go to **Settings → API**
   - Click the **"Legacy anon, service_role API keys"** tab
   - Copy the **`anon`** key (starts with `eyJ...`)

2. **Update Your `.env` File:**
   ```env
   VITE_SUPABASE_URL=https://chstjobzliwzqxmipsqs.supabase.co
   VITE_SUPABASE_PUBLISHABLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. **Restart Your Dev Server**

## ✅ Verification

After updating your `.env` file:

1. **Check Browser Console (F12)**
   - Should see NO errors about missing Supabase keys
   - Should see NO warnings about invalid key format

2. **Try Signing In**
   - Should work with correct credentials
   - If still failing, check console for specific error

## 🔍 How to Get the Full Key

In the Supabase dashboard, the key might be truncated with `...`. To get the full key:

1. **Click the copy icon** (📋) next to the key
2. **Or click the eye icon** (👁️) to reveal the full key
3. **Copy the entire key** - it's usually quite long

## 🐛 Troubleshooting

### Issue: "Invalid API key" Error

**Check:**
- ✅ Key is copied completely (no truncation)
- ✅ No extra spaces or quotes in `.env`
- ✅ Using `VITE_SUPABASE_PUBLISHABLE_KEY` (not `VITE_SUPABASE_ANON_KEY`)
- ✅ Dev server restarted after `.env` changes

### Issue: Key Format Warning

The code now accepts both formats:
- ✅ `sb_publishable_...` (new format)
- ✅ `eyJ...` (legacy format)

If you see a warning, double-check you copied the key correctly.

### Issue: Still Can't Sign In

1. **Check Browser Console** for specific error
2. **Verify Email Confirmation:**
   - Go to Supabase Dashboard → Authentication → Users
   - Check if your email is confirmed
3. **Try Signing Up Again:**
   - Use a fresh email
   - Complete email confirmation
   - Then try logging in

## 📝 Quick Checklist

- [ ] Copied the FULL publishable key from Supabase Dashboard
- [ ] Updated `frontend/.env` with the key
- [ ] Restarted dev server
- [ ] Browser console shows no Supabase errors
- [ ] Can sign in successfully

## 💡 Pro Tip

The **new publishable key format** (`sb_publishable_...`) is what Supabase recommends going forward. It's designed to be safer and more flexible. The code now supports both formats, so use whichever you prefer!


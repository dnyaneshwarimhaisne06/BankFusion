# Email Confirmation Fix - Complete Guide

## ✅ Issues Fixed

### 1. Route Mismatch ✅
- **Problem:** URL showed `/auth/verify` but route was `/auth/verified`
- **Fix:** Added both routes (`/auth/verify` and `/auth/verified`) for compatibility

### 2. Expired Link Handling ✅
- **Problem:** Expired links showed generic error
- **Fix:** 
  - Better error messages for expired links
  - Added "Request New Link" button
  - Added "Resend confirmation email" link on login page

### 3. Mobile Compatibility ✅
- **Problem:** Redirect URL used localhost (doesn't work on mobile)
- **Fix:** Uses `VITE_APP_URL` environment variable for production domain

## 🔧 Supabase Dashboard Configuration

### Step 1: Update Redirect URLs

Go to **Supabase Dashboard → Authentication → URL Configuration**

Add these **Redirect URLs** (one per line):

**For Development:**
```
http://localhost:5173/auth/verified
http://localhost:5173/auth/verify
http://localhost:5173/**
```

**For Production:**
```
https://yourdomain.com/auth/verified
https://yourdomain.com/auth/verify
https://yourdomain.com/**
```

### Step 2: Set Site URL

**For Development:**
```
http://localhost:5173
```

**For Production:**
```
https://yourdomain.com
```

## 🌍 Environment Variables

### Frontend `.env` File

**For Development:**
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
VITE_APP_URL=http://localhost:5173
```

**For Production:**
```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
VITE_APP_URL=https://yourdomain.com
```

**Important:** `VITE_APP_URL` should be your **publicly accessible domain** (not localhost) for mobile/other devices to work.

## 📱 How It Works Now

### Email Confirmation Flow

1. User signs up → Email sent with confirmation link
2. User clicks link (on any device) → Redirects to `/auth/verified` or `/auth/verify`
3. Page verifies email → Shows success message
4. User signs out automatically → Must log in manually
5. User logs in → Only works if email is confirmed

### Expired Link Handling

1. If link expired → Shows clear error message
2. User clicks "Request New Link" → Redirects to login
3. User enters email → Clicks "Resend confirmation email"
4. New email sent → User clicks new link

## 🧪 Testing

### Test on Desktop
1. Sign up with email
2. Check email for confirmation link
3. Click link → Should redirect to `/auth/verified`
4. Should show "Email verified successfully"
5. Log in → Should work

### Test on Mobile
1. Sign up with email (on desktop)
2. Open email on mobile
3. Click confirmation link
4. Should redirect to your domain (not localhost)
5. Should show verification page
6. Log in → Should work

### Test Expired Link
1. Wait for link to expire (or use old link)
2. Click expired link
3. Should show "link expired" message
4. Click "Request New Link"
5. Go to login page
6. Enter email and click "Resend confirmation email"
7. New email sent → Click new link

## ⚠️ Important Notes

1. **For Mobile/Other Devices:**
   - `VITE_APP_URL` must be your **public domain** (not localhost)
   - Example: `https://bankfusion.vercel.app` or `https://yourdomain.com`

2. **Supabase Redirect URLs:**
   - Must include both `/auth/verified` and `/auth/verify`
   - Must include your production domain
   - Wildcard `/**` allows all paths

3. **Email Links Expire:**
   - Default: 24 hours (Supabase setting)
   - Users can request new link from login page

4. **Development vs Production:**
   - Development: Use `localhost` URLs
   - Production: Use your deployed domain
   - Update both in Supabase dashboard

## 🐛 Troubleshooting

### Issue: Still redirects to localhost on mobile

**Solution:**
- Check `VITE_APP_URL` in `.env` file
- Should be your production domain (not localhost)
- Restart frontend server after changing `.env`

### Issue: "Link expired" error

**Solution:**
- Go to login page
- Enter your email
- Click "Resend confirmation email"
- Check email for new link
- Click new link (should work)

### Issue: 404 error on `/auth/verify`

**Solution:**
- Both routes are now added (`/auth/verify` and `/auth/verified`)
- Restart frontend server
- Clear browser cache

### Issue: Email confirmation doesn't work on mobile

**Solution:**
- Verify `VITE_APP_URL` is set to production domain
- Check Supabase redirect URLs include production domain
- Ensure production domain is publicly accessible
- Test with ngrok or similar for local testing on mobile

## ✅ Checklist

- [ ] Supabase redirect URLs configured (both `/auth/verified` and `/auth/verify`)
- [ ] `VITE_APP_URL` set to production domain (not localhost)
- [ ] Frontend server restarted
- [ ] Test email confirmation on desktop
- [ ] Test email confirmation on mobile
- [ ] Test expired link handling
- [ ] Test resend confirmation email


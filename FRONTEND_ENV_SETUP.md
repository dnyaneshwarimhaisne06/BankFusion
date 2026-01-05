# Frontend Environment Variable Setup for Render

## ⚠️ CRITICAL: Set VITE_FLASK_API_URL

The frontend **requires** `VITE_FLASK_API_URL` to be set in your Render environment variables.

## Steps to Fix "Failed to fetch" Error

### 1. Get Your Backend URL
Your backend is deployed on Render. Find the URL:
- Go to Render Dashboard → Your Backend Service
- Copy the URL (e.g., `https://bankfusion-backend-xxxx.onrender.com`)
- **Important:** Add `/api` to the end

### 2. Set Environment Variable in Render

**For Frontend Service:**
1. Go to Render Dashboard → Your Frontend Service
2. Click **"Environment"** tab
3. Click **"Add Environment Variable"**
4. Add:
   - **Key:** `VITE_FLASK_API_URL`
   - **Value:** `https://your-backend-url.onrender.com/api`
   - Example: `https://bankfusion-backend-0y57.onrender.com/api`
5. Click **"Save Changes"**
6. **Redeploy** your frontend service

### 3. Verify It's Set

After redeploying, check the browser console:
- Open DevTools (F12)
- Go to Console tab
- You should **NOT** see: `VITE_FLASK_API_URL is not configured`
- If you see that error, the variable is not set correctly

### 4. Test Upload

After setting the variable and redeploying:
1. Try uploading a PDF
2. Check Network tab - you should see the request to `/api/upload`
3. If it still fails, check the request URL in Network tab

## Common Issues

### Issue: "Failed to fetch" with nothing in Network tab
**Cause:** `VITE_FLASK_API_URL` is not set or is `undefined`
**Fix:** Set the environment variable as described above

### Issue: CORS error
**Cause:** Backend CORS not configured correctly
**Fix:** Already fixed in backend - ensure backend is redeployed

### Issue: 401 Unauthorized
**Cause:** Not logged in or token expired
**Fix:** Log in again

## Example Values

**Development (local):**
```env
VITE_FLASK_API_URL=http://localhost:5000/api
```

**Production (Render):**
```env
VITE_FLASK_API_URL=https://bankfusion-backend-0y57.onrender.com/api
```

## Important Notes

- The URL **must** end with `/api`
- The URL **must** be the full backend URL (not frontend URL)
- After setting the variable, you **must** redeploy the frontend
- The variable name is case-sensitive: `VITE_FLASK_API_URL` (all caps)


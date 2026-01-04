# Backend Supabase Configuration for Account Deletion

## ⚠️ Important

To enable account deletion, you **must** configure Supabase credentials in your backend `.env` file.

## Setup Steps

### 1. Get Your Supabase Service Role Key

1. Go to your Supabase Dashboard: https://app.supabase.com
2. Select your project
3. Navigate to **Settings** → **API**
4. Under **Project API keys**, find the **`service_role`** key (⚠️ **SECRET - Never expose this in frontend!**)
5. Copy the service role key

### 2. Update Backend `.env` File

Create or update `backend/.env` with:

```env
# Supabase Configuration (Required for account deletion)
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**Example:**
```env
SUPABASE_URL=https://chstjobzliwzqxmipsqs.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 3. Restart Backend Server

After updating `.env`:
```bash
# Stop the server (Ctrl+C)
cd backend
python app.py
```

## 🔐 Security Notes

- ✅ **Service Role Key** has admin privileges - keep it secret!
- ✅ Never commit `.env` file to git
- ✅ Only use service role key in backend/server code
- ✅ Frontend should NEVER have access to service role key

## ✅ Verification

After setup, try deleting an account. You should see in backend logs:
```
Successfully deleted Supabase user: <user_id>
```

If you see errors, check:
1. `.env` file has correct `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
2. Backend server was restarted after `.env` changes
3. Service role key is correct (not anon key)

## 🐛 Troubleshooting

### Error: "Supabase credentials not configured"

**Solution:** Add `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to `backend/.env`

### Error: "Failed to delete Supabase user: 401"

**Solution:** Check that you're using the **service_role** key, not the anon key

### Error: "Failed to delete Supabase user: 404"

**Solution:** Verify the `SUPABASE_URL` is correct and matches your project


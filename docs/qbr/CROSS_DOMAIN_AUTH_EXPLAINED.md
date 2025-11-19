# Cross-Domain Authentication Explained

**For Frontend Developers: How dashboards.enersystems.com authenticates with db-api.enersystems.com**

---

## Common Misconception

> "Since the frontend uses a different domain (dashboards.enersystems.com) than the backend (db-api.enersystems.com), when the frontend authenticates with Microsoft 365, it can't pass the token to the backend."

**This is incorrect.** The frontend never handles tokens. The browser handles everything automatically.

---

## How It Actually Works

### 1. Authentication Flow (All Browser Redirects - No Frontend Code)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1: User clicks "Login with Microsoft" button                  │
│ Frontend: window.location.href = 'https://db-api.enersystems.com:5400/api/auth/microsoft/login'
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 2: Backend redirects browser to Microsoft                     │
│ Location: https://login.microsoftonline.com/...                    │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 3: User logs in at Microsoft (enters password)                │
│ Microsoft validates credentials                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 4: Microsoft redirects browser back to backend callback       │
│ Location: https://db-api.enersystems.com:5400/api/auth/microsoft/callback?code=...
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 5: Backend exchanges code for token (server-side)             │
│ Backend validates user email against whitelist                     │
│ Backend creates session in /tmp/flask_sessions/                    │
│ Backend sets HTTP-only cookie: session=abc123                      │
│   Domain: db-api.enersystems.com                                   │
│   Secure: true (HTTPS only)                                        │
│   HttpOnly: true (JavaScript cannot access)                        │
│   SameSite: Lax (allows cross-origin with GET)                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 6: Backend redirects browser to frontend                      │
│ Location: https://dashboards.enersystems.com/qbr                   │
│ Browser now has session cookie for db-api.enersystems.com domain   │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 7: Frontend loads, makes API request                          │
│ fetch('https://db-api.enersystems.com:5400/api/qbr/smartnumbers', {│
│   credentials: 'include'  // This is the magic line                │
│ })                                                                  │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 8: Browser automatically includes session cookie              │
│ Request to: https://db-api.enersystems.com:5400                    │
│ Cookie header: session=abc123                                      │
│ (Browser adds this automatically - frontend code doesn't touch it) │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 9: Backend validates session                                  │
│ Looks up session file in /tmp/flask_sessions/                      │
│ Checks user_email against whitelist                                │
│ Returns data if valid, 401 if not                                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Technical Concepts

### HTTP-Only Cookies Work Across Different Domains

**Fact**: When you set a cookie for `db-api.enersystems.com`, the browser will **automatically** include that cookie in **any request** to `https://db-api.enersystems.com:5400/*`, regardless of which domain the request originates from.

**Example**:
- Cookie is set for: `db-api.enersystems.com`
- Frontend runs at: `dashboards.enersystems.com`
- API request goes to: `https://db-api.enersystems.com:5400/api/qbr/smartnumbers`
- Browser sees: "This request is going to db-api.enersystems.com, and I have a cookie for that domain"
- Browser automatically includes: `Cookie: session=abc123` in the request header

**The frontend code never touches the cookie. The browser does it automatically.**

### CORS (Cross-Origin Resource Sharing)

The backend is configured to allow cross-origin requests from `https://dashboards.enersystems.com`:

```python
# In api_server.py
CORS(app, supports_credentials=True, origins=[
    'https://dashboards.enersystems.com',
    'https://db-api.enersystems.com:5400'
])
```

This tells the browser: "Yes, dashboards.enersystems.com is allowed to make requests to this API with credentials."

### credentials: 'include'

This is the **only thing** the frontend code needs to do:

```javascript
fetch('https://db-api.enersystems.com:5400/api/qbr/smartnumbers', {
  credentials: 'include'  // Tells browser to include cookies for db-api.enersystems.com
})
```

Without `credentials: 'include'`, the browser would **not** send cookies in cross-origin requests (for security). With it, the browser sends cookies that match the target domain.

---

## What The Frontend Does NOT Do

❌ **Does NOT receive tokens from Microsoft** (backend does this)
❌ **Does NOT store tokens** (backend does this in session file)
❌ **Does NOT pass tokens to backend** (browser passes session cookie automatically)
❌ **Does NOT handle OAuth flow** (backend redirects, browser follows)
❌ **Does NOT access cookies** (HTTP-only flag prevents JavaScript access)
❌ **Does NOT validate authentication** (backend does this on every request)

---

## What The Frontend DOES Do

✅ **Redirect to login** when user clicks "Login with Microsoft"
✅ **Include `credentials: 'include'` in API requests** (tells browser to send cookies)
✅ **Handle 401 errors** (redirect back to login when session expires)
✅ **Display user info** (from `/api/auth/status` response)
✅ **Provide logout button** (redirect to `/api/auth/logout`)

---

## Code Examples

### Login Button (Frontend)
```javascript
const handleLogin = () => {
  // Just redirect to backend login endpoint
  // Backend handles OAuth, sets cookie, redirects back
  window.location.href = 'https://db-api.enersystems.com:5400/api/auth/microsoft/login';
};

return <button onClick={handleLogin}>Login with Microsoft</button>;
```

### Check Auth Status on App Load (Frontend)
```javascript
useEffect(() => {
  fetch('https://db-api.enersystems.com:5400/api/auth/status', {
    credentials: 'include'  // Browser sends session cookie automatically
  })
    .then(res => res.json())
    .then(data => {
      if (data.authenticated) {
        setUser(data);  // { user_email, user_name, login_time }
        navigate('/dashboard');
      } else {
        navigate('/login');
      }
    });
}, []);
```

### Fetch SmartNumbers (Frontend)
```javascript
fetch('https://db-api.enersystems.com:5400/api/qbr/smartnumbers?period=2025-Q4', {
  credentials: 'include'  // Browser sends session cookie automatically
})
  .then(res => {
    if (res.status === 401) {
      // Session expired, redirect to login
      window.location.href = '/login';
      return;
    }
    return res.json();
  })
  .then(data => {
    setSmartNumbers(data.data.smartnumbers);
  });
```

### Using Axios (Alternative)
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'https://db-api.enersystems.com:5400',
  withCredentials: true  // Equivalent to credentials: 'include'
});

// All requests automatically include credentials
const response = await api.get('/api/qbr/smartnumbers?period=2025-Q4');
```

---

## Testing Cross-Domain Auth

### Step 1: Login via Browser
1. Open browser on LAN/VPN
2. Navigate to: `https://db-api.enersystems.com:5400/api/auth/microsoft/login`
3. Login with `rmmiller@enersystems.com` or `jmmiller@enersystems.com`
4. After success, you'll be at: `https://dashboards.enersystems.com/qbr`

### Step 2: Check Session Cookie in DevTools
1. Press F12 to open DevTools
2. Go to **Application** tab (Chrome) or **Storage** tab (Firefox)
3. Look under **Cookies** → `https://db-api.enersystems.com:5400`
4. You should see a cookie named `session` with:
   - Domain: `db-api.enersystems.com`
   - HttpOnly: ✓ (checked)
   - Secure: ✓ (checked)
   - SameSite: Lax

### Step 3: Test API Request in DevTools Console
```javascript
// Run this in browser console on dashboards.enersystems.com
fetch('https://db-api.enersystems.com:5400/api/auth/status', {
  credentials: 'include'
})
  .then(res => res.json())
  .then(data => console.log(data));

// Should return:
// { authenticated: true, user_email: "rmmiller@enersystems.com", user_name: "Ryan Miller", ... }
```

### Step 4: Watch Network Tab
1. Open DevTools → Network tab
2. Make the fetch request above
3. Click on the `status` request
4. Look at **Request Headers** → You'll see: `Cookie: session=abc123...`
5. This proves the browser automatically included the cookie

---

## Why This Works

This is **standard web authentication** used by millions of websites:

- **Google Sign-In**: Your app domain ≠ Google domain, but OAuth works
- **Facebook Login**: Your app domain ≠ Facebook domain, but OAuth works
- **GitHub OAuth**: Your app domain ≠ GitHub domain, but OAuth works

**All use the same pattern**:
1. App redirects to OAuth provider
2. User logs in
3. OAuth provider redirects back with code
4. Backend exchanges code for token (server-side)
5. Backend creates session, sets HTTP-only cookie
6. Frontend makes API calls with `credentials: 'include'`
7. Browser automatically includes cookies

---

## Security Benefits

### Why HTTP-Only Cookies Are Safer Than Frontend Tokens

**If frontend stores tokens** (localStorage, sessionStorage):
- ❌ Vulnerable to XSS attacks (malicious JavaScript can steal tokens)
- ❌ Frontend code can accidentally log tokens
- ❌ Browser extensions can read tokens

**With HTTP-Only Cookies**:
- ✅ JavaScript **cannot access** the cookie (HttpOnly flag)
- ✅ Only sent over HTTPS (Secure flag)
- ✅ Browser manages inclusion automatically
- ✅ Backend validates on every request
- ✅ XSS attacks cannot steal session cookies

---

## Common Questions

### Q: "But the frontend and backend are different domains. How does the cookie work?"

**A**: The cookie is for `db-api.enersystems.com`. When the frontend makes a request **to** `db-api.enersystems.com`, the browser automatically includes cookies for that domain. It doesn't matter where the request originates from - what matters is where it's going.

### Q: "Does the frontend need to send the cookie in the request?"

**A**: No! The browser does this automatically when you use `credentials: 'include'`. The frontend never touches the cookie.

### Q: "Can I test this with curl?"

**A**: Not easily. HTTP-only cookies are designed to be browser-only. You'd need to manually extract the cookie from the browser and include it in curl with `-b` flag. It's better to test in the browser DevTools.

### Q: "What if I want to test without Microsoft OAuth?"

**A**: Use the temporary test endpoint that doesn't require auth:
```bash
curl -k https://db-api.enersystems.com:5400/api/qbr/test/smartnumbers?period=2025-Q3
```

### Q: "Where is the session stored?"

**A**: Server-side in `/tmp/flask_sessions/`. The cookie only contains a session ID - the actual user data is on the backend.

### Q: "What happens when session expires?"

**A**: After 8 hours (configurable), the session file is deleted. Next API request returns 401. Frontend detects 401 and redirects to login.

---

## Troubleshooting

### Frontend makes API call but gets 401

**Possible causes**:
1. User not logged in yet → Redirect to `/login`
2. Session expired (8 hours) → Redirect to `/login`
3. Missing `credentials: 'include'` → Add it to fetch/axios config

**Check in DevTools**:
- Network tab → Click request → Headers
- Look for `Cookie:` header in Request Headers
- If missing, you forgot `credentials: 'include'`

### CORS error in browser console

**Error**: "Access to fetch at 'https://db-api.enersystems.com:5400/api/qbr/smartnumbers' from origin 'https://dashboards.enersystems.com' has been blocked by CORS policy"

**Cause**: Backend CORS not configured to allow `dashboards.enersystems.com`

**Fix**: Already configured in our setup. If you see this, the API server might not be running.

### Cookie not being set after login

**Check**:
1. Did you successfully login at Microsoft? (should redirect back to frontend)
2. Is user email in whitelist? (QBR_AUTHORIZED_USERS in /opt/shared-secrets/api-secrets.env)
3. Check backend logs: `sudo journalctl -u es-inventory-api.service -n 50`

---

## Summary: What You Need To Remember

1. **Frontend never handles OAuth tokens** - Backend does everything
2. **Session cookie is for db-api.enersystems.com domain** - Browser includes it automatically
3. **Always use `credentials: 'include'`** - This tells browser to send cookies
4. **Handle 401 errors** - Redirect to login when session expires
5. **CORS is already configured** - Backend allows dashboards.enersystems.com with credentials

**Just redirect to login, include credentials in API calls, and handle 401s. The browser does the rest.**

---

## Additional Resources

- **FRONTEND_DEVELOPMENT_BRIEF.md** - Complete frontend implementation guide
- **QBR_API_DOCUMENTATION.md** - API endpoints and request/response formats
- **PLANNING_DECISIONS.md** (Section 16) - Authentication architecture decisions
- **AUTHENTICATION_IMPLEMENTATION.md** - Backend implementation details
- **AZURE_AD_SETUP_GUIDE.md** - How Azure AD was configured

---

**Backend Status**: ✅ OAuth implemented and tested
**Frontend Task**: Redirect to login, use `credentials: 'include'`, handle 401s
**Estimated Time**: 2-4 hours for basic auth integration

**You've got this!** 🚀

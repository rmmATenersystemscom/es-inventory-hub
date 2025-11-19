# Azure AD Setup Guide for QBR Dashboard Authentication

**Purpose**: Step-by-step guide to register the QBR Dashboard application in Azure Active Directory for Microsoft 365 Single Sign-On (SSO)

**Estimated Time**: 10-15 minutes
**Prerequisites**: Global Admin access to Azure Portal
**Status**: Ready to execute

---

## Overview

This guide will walk you through creating an Azure AD app registration that enables your QBR Dashboard to authenticate users via Microsoft 365.

**What You're Setting Up:**
- App Registration in Azure AD
- OAuth 2.0 authentication flow
- Permissions for reading user profile (email, name)
- Redirect URI for authentication callback

**Security:**
- Only 2 specific email addresses will be authorized
- Backend validates email against whitelist
- Tokens expire after 8 hours
- HTTPS-only communication

---

## Step 1: Access Azure Portal

1. Open web browser and go to: **https://portal.azure.com**
2. Sign in with your Global Admin credentials
3. Wait for portal to load

**Screenshot location:** You should see "Microsoft Azure" in the top-left corner

---

## Step 2: Navigate to Azure Active Directory

1. In the left sidebar, click **"Azure Active Directory"**
   - If you don't see it, click the hamburger menu (☰) in the top-left
   - Or use the search bar at the top and search for "Azure Active Directory"

2. You should now see the Azure AD Overview page

**What you'll see:**
- Tenant name (likely "Enersystems" or similar)
- Tenant ID (a UUID like `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
- Domain name (enersystems.onmicrosoft.com or custom domain)

**📋 ACTION:** Copy your **Tenant ID** and save it - you'll need this later!

```
Tenant ID: _________________________________
```

---

## Step 3: Create App Registration

1. In the Azure AD left sidebar, click **"App registrations"**
2. Click **"+ New registration"** button at the top
3. Fill out the registration form:

### Registration Form Details:

**Name:**
```
QBR Dashboard
```

**Supported account types:**
- ✅ Select: **"Accounts in this organizational directory only (Enersystems only - Single tenant)"**
- ❌ Do NOT select "Multitenant" or "Personal Microsoft accounts"

**Redirect URI:**
- Platform: **Web** (use dropdown)
- URI:
```
https://db-api.enersystems.com:5400/api/auth/microsoft/callback
```

**Important:** Make sure there are no typos in the redirect URI!

4. Click **"Register"** button at the bottom

---

## Step 4: Copy Application (Client) ID

After clicking Register, you'll be taken to the app's Overview page.

**📋 ACTION:** Copy the **Application (client) ID** and save it:

```
Application (client) ID: _________________________________
```

This is a UUID that looks like: `12345678-1234-1234-1234-123456789abc`

**⚠️ Important:** This is different from the Tenant ID you copied earlier!

---

## Step 5: Create Client Secret

1. In the left sidebar of your app, click **"Certificates & secrets"**
2. Click the **"Client secrets"** tab (should be selected by default)
3. Click **"+ New client secret"**

**Add a client secret:**
- Description: `QBR Dashboard Backend Secret`
- Expires: **24 months** (or choose your preference - can be renewed before expiration)

4. Click **"Add"**

**📋 ACTION:** IMMEDIATELY copy the **Value** (NOT the Secret ID):

```
Client Secret Value: _________________________________
```

**⚠️ CRITICAL:** You can only see this value ONCE! If you miss it, you'll have to create a new secret.

The value will look like: `AbC123~xYz789-1234567890aBcDeFgHiJkLmNoPqRsTuVwXyZ`

**Security Note:** This secret is like a password for your application. Keep it secure!

---

## Step 6: Configure API Permissions

1. In the left sidebar, click **"API permissions"**
2. You should see "User.Read" already listed (Microsoft Graph)
3. This is all we need! ✅

**What "User.Read" allows:**
- Read the signed-in user's email address
- Read the signed-in user's display name
- Read basic profile information

**We do NOT need:**
- Access to user's files
- Access to other users' data
- Write permissions
- Admin permissions

**✅ No action needed - default permissions are perfect!**

---

## Step 7: Verify Configuration

Let's double-check everything is correct:

### Overview Page Check:
1. Go back to **"Overview"** in the left sidebar
2. Verify these settings:

**Application name:** QBR Dashboard ✅
**Application (client) ID:** `[UUID you saved]` ✅
**Directory (tenant) ID:** `[UUID you saved]` ✅
**Supported account types:** Single tenant ✅

### Authentication Check:
1. Click **"Authentication"** in the left sidebar
2. Under "Platform configurations", verify:

**Web redirect URI:** `https://db-api.enersystems.com:5400/api/auth/microsoft/callback` ✅

3. Scroll down to "Advanced settings"
4. Verify these are set:

**Allow public client flows:** NO ✅
**Supported account types:** Single tenant ✅

---

## Step 8: Summary - Information to Provide

You should now have these 3 values saved:

```
1. Tenant ID: _________________________________

2. Application (client) ID: _________________________________

3. Client Secret Value: _________________________________
```

**Next Steps:**
1. Provide these 3 values to configure the backend
2. Values will be stored securely in `/opt/shared-secrets/api-secrets.env`
3. Backend will use these to authenticate users via Microsoft 365

---

## Security Best Practices

### Secret Storage:
- ✅ Store in `/opt/shared-secrets/api-secrets.env` (secure file)
- ✅ File permissions: `600` (owner read/write only)
- ✅ Never commit to git
- ✅ Never share in chat/email/screenshots

### Secret Rotation:
- Client secrets expire (you chose 24 months)
- Azure will warn you 30 days before expiration
- You can create a new secret before the old one expires
- Update backend config with new secret
- Old secret still works until expiration (no downtime)

### Monitoring:
- Azure AD logs all sign-in attempts
- You can view who logged in and when
- Location: Azure Portal → Azure AD → Sign-in logs

---

## Troubleshooting

### "Redirect URI mismatch" error:
- Double-check the URI is exactly: `https://db-api.enersystems.com:5400/api/auth/microsoft/callback`
- No trailing slash
- HTTPS (not HTTP)
- Correct port (5400)

### "Application not found" error:
- Make sure you're using the Application (client) ID, not the Object ID
- Copy from the Overview page

### "Invalid client secret" error:
- Make sure you copied the Value, not the Secret ID
- If you missed it, create a new secret
- Secrets are case-sensitive

### User can't sign in:
- User's email must be: `rmmiller@enersystems.com` or `jmmiller@enersystems.com`
- User must be in your Microsoft 365 tenant
- Check backend logs for authorization errors

---

## Testing the Setup

Once the backend is configured with your 3 values, you can test:

1. Visit: `https://db-api.enersystems.com:5400/api/auth/microsoft/login`
2. You should be redirected to Microsoft login
3. Sign in with rmmiller@enersystems.com or jmmiller@enersystems.com
4. Consent to permissions (first time only)
5. Should redirect back to dashboard

**If this works:** ✅ Azure AD setup is complete!

---

## Authorized Users

**Current authorized users:**
- rmmiller@enersystems.com
- jmmiller@enersystems.com

**To add more users later:**
- Update backend configuration (no Azure changes needed)
- Edit `AUTHORIZED_USERS` list in backend code
- Restart API server

---

## Additional Resources

**Azure AD App Registration Documentation:**
https://docs.microsoft.com/en-us/azure/active-directory/develop/quickstart-register-app

**OAuth 2.0 Flow Diagram:**
https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-auth-code-flow

**Microsoft Identity Platform:**
https://docs.microsoft.com/en-us/azure/active-directory/develop/

---

## Completed Checklist

Before providing the credentials to configure backend:

- [ ] Created app registration named "QBR Dashboard"
- [ ] Set redirect URI to `https://db-api.enersystems.com:5400/api/auth/microsoft/callback`
- [ ] Saved Tenant ID
- [ ] Saved Application (client) ID
- [ ] Created and saved Client Secret Value
- [ ] Verified "User.Read" permission exists
- [ ] Verified single-tenant configuration
- [ ] Ready to provide 3 values for backend configuration

---

**Version**: v1.0
**Created**: November 16, 2025
**For**: QBR Dashboard Microsoft 365 SSO
**Security Level**: Single tenant, 2 authorized users
**Next Steps**: Provide credentials → Backend implementation → Testing


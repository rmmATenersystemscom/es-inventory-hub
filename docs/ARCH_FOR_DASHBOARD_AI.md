# Guide: Creating Dashboard AI Prompts

This guide explains how to create reference documentation (prompts) for Dashboard AI and make them accessible via HTTPS.

## Overview

Dashboard AI prompts are markdown files that provide API documentation, schema references, and integration guides. They are stored in `/opt/es-inventory-hub/prompts/` and served via the API server at `https://db-api.enersystems.com:5400/prompts/`.

## Directory Structure

```
/opt/es-inventory-hub/
├── prompts/                          # Dashboard AI reference documents
│   ├── ninja-usage-changes-api.md    # Example: Ninja API reference
│   └── your-new-prompt.md            # Your new prompt file
└── docs/                             # Internal project documentation
```

## Step-by-Step: Creating a New Prompt

### Step 1: Create the Markdown File

Create your prompt file in the `/opt/es-inventory-hub/prompts/` directory:

```bash
# Create/edit the file
nano /opt/es-inventory-hub/prompts/your-prompt-name.md
```

### Step 2: Follow the Standard Structure

Use this template for consistency:

```markdown
# [Feature Name] - Dashboard AI Reference

## Overview

Brief description of what this API/feature does and why Dashboard AI would use it.

## Endpoint

```
GET /api/your-endpoint
```

**Authentication:** Required (Microsoft OAuth via session cookie)

## Purpose

Bullet points explaining the main use cases.

## Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `param1` | string | Yes | - | Description |
| `param2` | string | No | `default` | Description |

## Response Structure

```json
{
  "success": true,
  "data": {
    // Example response
  }
}
```

## Field Definitions

| Field | Type | Description |
|-------|------|-------------|
| `field1` | string | What this field contains |

## Error Responses

Document common error codes and their meanings.

## Usage Examples

Show practical API call examples.

## Dashboard Use Cases

1. **Use Case 1** - Description
2. **Use Case 2** - Description

---

**Version**: vX.Y.Z
**Last Updated**: [Date] UTC
**Maintainer**: ES Inventory Hub Team
```

### Step 3: Set File Permissions

**CRITICAL**: The API server runs as a different user. Files must be world-readable:

```bash
chmod 644 /opt/es-inventory-hub/prompts/your-prompt-name.md
```

Verify permissions:
```bash
ls -la /opt/es-inventory-hub/prompts/
# Should show: -rw-r--r-- (644)
```

### Step 4: Test HTTPS Access

Verify the prompt is accessible:

```bash
# Local test
curl -sk "https://localhost:5400/prompts/your-prompt-name.md" | head -20

# Full URL test
curl -sk "https://db-api.enersystems.com:5400/prompts/your-prompt-name.md" | head -20
```

### Step 5: Provide URL to Dashboard AI

The prompt is now accessible at:

```
https://db-api.enersystems.com:5400/prompts/your-prompt-name.md
```

Dashboard AI can fetch this URL to read the documentation.

## How the `/prompts/` Endpoint Works

The API server (`api/api_server.py`) includes a route that serves files from the prompts directory:

```python
@app.route('/prompts/<path:filename>')
def serve_prompt(filename):
    """Serve prompt files for Dashboard AI."""
    prompts_dir = Path(__file__).parent.parent / 'prompts'
    return send_from_directory(prompts_dir, filename)
```

- **No authentication required** - Prompts are public reference docs
- **Read-only** - Only serves existing files, no uploads
- **Markdown only** - Designed for `.md` files

## Common Issues

### Permission Denied Error

**Symptom**: API returns "PermissionError: Permission denied"

**Cause**: File permissions are too restrictive (e.g., `600` or `640`)

**Fix**:
```bash
chmod 644 /opt/es-inventory-hub/prompts/your-file.md
```

### 404 Not Found

**Symptom**: API returns 404 error

**Cause**: File doesn't exist or filename is wrong

**Fix**: Verify the file exists:
```bash
ls -la /opt/es-inventory-hub/prompts/
```

### File Not Updating

**Symptom**: Old content still showing after edits

**Cause**: Browser or proxy caching

**Fix**: Add cache-busting parameter or wait for cache expiry:
```bash
curl -sk "https://db-api.enersystems.com:5400/prompts/your-file.md?v=2"
```

## Naming Conventions

Use lowercase with hyphens:
- `ninja-usage-changes-api.md` (API reference)
- `quickbooks-web-connector-setup.md` (Setup guide)
- `device-snapshot-schema.md` (Schema reference)

## Existing Prompts

| File | Purpose |
|------|---------|
| `ninja-usage-changes-api.md` | Ninja device change tracking API reference |

## Checklist for New Prompts

- [ ] Created file in `/opt/es-inventory-hub/prompts/`
- [ ] Used standard markdown template structure
- [ ] Set permissions to `644` (`chmod 644 filename.md`)
- [ ] Tested local access via `curl`
- [ ] Tested HTTPS access via full URL
- [ ] Added version footer with date
- [ ] Committed to git repository

## Related Documentation

- [API Integration Guide](./API_INTEGRATION.md) - Full API documentation
- [CHECK-IN Process](./STD_AI_CHECK_IN_PROCESS.md) - Git commit workflow

---

**Version**: v1.32.0
**Last Updated**: December 18, 2025 22:10 UTC
**Maintainer**: ES Inventory Hub Team

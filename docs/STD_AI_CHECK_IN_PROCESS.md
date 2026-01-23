# CHECK-IN Process

When the user types **"CHECK-IN!"**, execute the git commit and versioning process below.

---

## Required Output Format

**Use this exact format for your response:**

```
CHECK-IN COMPLETE! ✅

Tag Used: vX.Y.Z

Changes Committed:
- [First change description]
- [Second change description]
- [Continue for all changes...]

Files Modified:
- filename.py - Description of changes
- filename.md - Description of changes

The changes have been successfully committed and pushed to GitHub with tag vX.Y.Z
All detailed revision notes are preserved in Git tag messages and commit history
```

---

## Workflow Checklist

### 1. Determine Version
```bash
git tag --sort=-version:refname | head -5
```
- **Patch** (v1.38.10 → v1.38.11): Bug fixes, minor changes
- **Minor** (v1.38.11 → v1.39.0): New features, new endpoints
- **Major** (v1.39.0 → v2.0.0): Breaking changes

### 2. Update README.md
- Update `**Current Version**: vX.Y.Z` at top
- Add new version section, shift previous versions down

### 3. Update Modified .md Files
For any `.md` files being committed, update the footer:
```markdown
---

**Version**: vX.Y.Z
**Last Updated**: [Current UTC date/time]
**Maintainer**: ES Inventory Hub Team
```

### 4. Git Operations
```bash
git add .
git commit -m "Release vX.Y.Z: [Brief description]"
git tag -a vX.Y.Z -m "[Change description]"
git push origin main --tags
```

### 5. Verify & Report
```bash
git status  # Should show "nothing to commit, working tree clean"
```
Then output the **Required Output Format** above.

---

## Example

```
CHECK-IN COMPLETE! ✅

Tag Used: v1.38.11

Changes Committed:
- Changed database unique constraint to prevent duplicate records
- API now returns only the latest value per metric
- Cleaned up 146 stale duplicate records

Files Modified:
- README.md - Updated version to v1.38.11
- api/qbr_api.py - Fixed query to return latest values
- api/qbwc_service.py - Removed vendor_id from uniqueness check

The changes have been successfully committed and pushed to GitHub with tag v1.38.11
All detailed revision notes are preserved in Git tag messages and commit history
```

---

**Version**: v1.38.11
**Last Updated**: January 23, 2026 20:15 UTC
**Maintainer**: ES Inventory Hub Team

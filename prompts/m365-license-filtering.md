# M365 License Filtering Question

I'm building a new M365 collector for es-inventory-hub that will pull data via the Microsoft Graph API. The collector needs to replicate the same user counts shown in the current M365 dashboard.

## Current Dashboard Output
The M365 dashboard export shows:
- 37 organizations
- Fields: Organization, User Count

## Questions for Dashboard AI

1. **Which M365 license SKUs are included when calculating "User Count"?**
   - Are all license types counted, or only specific SKUs (e.g., Business Basic, Business Premium, E3, E5)?
   - Is there a whitelist or blacklist of SKU part numbers?

2. **How is the user count calculated?**
   - Is it counting users with ANY license from the included SKUs?
   - Or is it summing consumed units from subscribedSkus endpoint?

3. **Are any licenses explicitly excluded?**
   - Free licenses (e.g., MICROSOFT_TEAMS_EXPLORATORY)?
   - Trial licenses?
   - Add-on licenses (e.g., Audio Conferencing, Phone System)?
   - Exchange Online only plans?

4. **Is there any SKU mapping file or configuration that defines which licenses to include?**
   - The API docs mention `sku_mapping.csv` - does this contain the filter logic?

5. **Are there any tenant-level filters?**
   - Are any tenants excluded from the count?

Please provide the specific SKU part numbers or GUIDs that should be included/excluded so the new collector produces matching user counts.

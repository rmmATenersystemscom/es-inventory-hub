#!/usr/bin/env bash
set -euo pipefail
cd /opt/es-inventory-hub
source .venv/bin/activate
export $(grep '^DB_DSN=' .env)

# 1) Drop today's TL snapshot (vendor_id=4), so removed devices disappear
psql -U postgres -h localhost -d es_inventory_hub -c "
DELETE FROM device_snapshot
WHERE snapshot_date = CURRENT_DATE AND vendor_id = 4;"

# 2) Recollect TL (full)
python -m collectors.threatlocker.main

# 3) Clear today's exceptions and rebuild via checks
psql -U postgres -h localhost -d es_inventory_hub -c "
DELETE FROM exceptions WHERE date_found = CURRENT_DATE;"
python -m collectors.threatlocker.main --limit 1

# 4) Show summary + current missing list (15-char, case-insensitive, domain-stripped)
echo -e "\n== Exception counts (today) =="
psql -U postgres -h localhost -d es_inventory_hub -c "
SELECT type, COUNT(*) FROM exceptions
WHERE date_found=CURRENT_DATE GROUP BY type ORDER BY type;"

echo -e "\n== ThreatLocker in TL but not in Ninja (today) =="
psql -U postgres -h localhost -d es_inventory_hub -c "
WITH tl AS (
  SELECT hostname, LEFT(LOWER(SPLIT_PART(hostname,'.',1)),15) AS base
  FROM device_snapshot
  WHERE snapshot_date=CURRENT_DATE AND vendor_id=4
),
nj AS (
  SELECT DISTINCT LEFT(LOWER(SPLIT_PART(hostname,'.',1)),15) AS base
  FROM device_snapshot
  WHERE snapshot_date=CURRENT_DATE AND vendor_id=3
)
SELECT tl.hostname
FROM tl LEFT JOIN nj USING(base)
WHERE nj.base IS NULL
ORDER BY tl.hostname;"

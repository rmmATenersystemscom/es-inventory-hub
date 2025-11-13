# System Architecture – QBR Web Dashboard

## Overview
Two coordinated servers form the QBR Web Dashboard system:

- **Backend Server (Database AI)** — Performs ETL, hosts PostgreSQL, and exposes REST API.
- **Frontend Server (Dashboard AI)** — Displays charts/tables using data fetched from backend.

## Data Flow
1. Dashboard sends requests → Backend API (`https://db-api.enersystems.com:5400`)
2. Backend authenticates using `X-API-Key`
3. Backend retrieves/aggregates data from PostgreSQL or external APIs
4. Backend responds with JSON
5. Dashboard renders via Bootstrap + Chart.js

## Security
- HTTPS only (TLS 1.2+)
- API key + optional IP allowlist
- LAN-only connectivity
- Shared secrets in `/opt/shared-secrets/api-secrets.env`

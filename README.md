# ES Inventory Hub

A centralized inventory management system for collecting and storing data from various sources including Ninja and ThreatLocker.

## Overview

This repository contains the core infrastructure for the ES Inventory Hub, providing data collection, storage, and management capabilities for enterprise security inventory tracking.

## Environment Configuration

**Note:** The `.env` file is symlinked and not managed in this repository. Please ensure your environment variables are properly configured in the linked location.

## Project Structure

- `collectors/` - Data collection modules for various sources
- `storage/` - Database models and migration scripts
- `dashboard_diffs/` - Dashboard comparison and diff utilities
- `common/` - Shared utilities and common functionality
- `docker/` - Docker configuration files
- `tests/` - Test suite
- `scripts/` - Utility scripts
- `ops/` - Operations and deployment scripts

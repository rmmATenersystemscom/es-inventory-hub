# Collector Run Tracking API

This document describes the new collector run tracking API endpoints that provide real-time progress monitoring for collector runs.

## Overview

The collector run tracking system provides:
- **Batch tracking**: Group multiple collector runs together
- **Job tracking**: Individual collector run progress
- **Real-time status**: Live progress updates with percentages and messages
- **History**: Complete run history with durations and status
- **Polling support**: Designed for 5-10 second polling intervals

## API Endpoints

### 1. Trigger Collector Run

**POST** `/api/collectors/run`

Triggers one or more collectors and returns batch and job IDs for tracking.

**Request Body:**
```json
{
  "collectors": ["ninja", "threatlocker"],
  "priority": "normal"
}
```

**Response (201):**
```json
{
  "batch_id": "bc_12345678",
  "collectors": [
    {
      "job_name": "ninja-collector",
      "job_id": "ni_87654321",
      "status": "queued",
      "started_at": "2025-10-06T15:16:10.552780Z"
    },
    {
      "job_name": "threatlocker-collector", 
      "job_id": "th_11223344",
      "status": "queued",
      "started_at": "2025-10-06T15:16:10.552780Z"
    }
  ]
}
```

### 2. Get Batch Status

**GET** `/api/collectors/runs/batch/{batch_id}`

Returns the status of a specific batch run with all associated jobs.

**Response (200):**
```json
{
  "batch_id": "bc_12345678",
  "status": "running",
  "progress_percent": 62,
  "estimated_completion": "2025-10-06T15:17:45Z",
  "started_at": "2025-10-06T15:16:10.552780Z",
  "updated_at": "2025-10-06T15:16:45.123456Z",
  "ended_at": null,
  "message": "Processing collectors...",
  "error": null,
  "collectors": [
    {
      "job_name": "ninja-collector",
      "job_id": "ni_87654321",
      "status": "running",
      "started_at": "2025-10-06T15:16:10.552780Z",
      "updated_at": "2025-10-06T15:16:45.123456Z",
      "ended_at": null,
      "progress_percent": 70,
      "message": "Processing page 7/10",
      "error": null,
      "duration_seconds": null
    }
  ],
  "duration_seconds": null
}
```

### 3. Get Job Status

**GET** `/api/collectors/runs/job/{job_id}`

Returns the status of a specific job run.

**Response (200):**
```json
{
  "job_id": "ni_87654321",
  "batch_id": "bc_12345678",
  "job_name": "ninja-collector",
  "status": "running",
  "started_at": "2025-10-06T15:16:10.552780Z",
  "updated_at": "2025-10-06T15:16:45.123456Z",
  "ended_at": null,
  "progress_percent": 70,
  "message": "Processing page 7/10",
  "error": null,
  "duration_seconds": null,
  "batch_status": "running",
  "batch_progress_percent": 62,
  "estimated_completion": "2025-10-06T15:17:45Z",
  "batch_message": "Processing collectors..."
}
```

### 4. Get Latest Runs

**GET** `/api/collectors/runs/latest?collectors=ninja,threatlocker`

Returns the latest active or most recent terminal runs for specified collectors.

**Response (200):**
```json
{
  "latest_runs": [
    {
      "job_id": "ni_87654321",
      "batch_id": "bc_12345678",
      "job_name": "ninja-collector",
      "status": "running",
      "started_at": "2025-10-06T15:16:10.552780Z",
      "updated_at": "2025-10-06T15:16:45.123456Z",
      "ended_at": null,
      "progress_percent": 70,
      "message": "Processing page 7/10",
      "error": null,
      "duration_seconds": null,
      "batch_status": "running",
      "batch_progress_percent": 62,
      "estimated_completion": "2025-10-06T15:17:45Z",
      "batch_message": "Processing collectors..."
    }
  ],
  "total_runs": 1,
  "generated_at": "2025-10-06T15:16:45.123456Z"
}
```

### 5. Get Run History

**GET** `/api/collectors/history?limit=10`

Returns recent collector runs including running jobs.

**Response (200):**
```json
{
  "collection_history": [
    {
      "job_id": "ni_87654321",
      "job_name": "ninja-collector",
      "started_at": "2025-10-06T15:16:10.552780Z",
      "ended_at": "2025-10-06T15:17:30.123456Z",
      "status": "completed",
      "message": "Collection completed successfully",
      "progress_percent": 100,
      "updated_at": "2025-10-06T15:17:30.123456Z",
      "duration": "1m 20s",
      "duration_seconds": 80
    }
  ],
  "total_runs": 1,
  "generated_at": "2025-10-06T15:17:30.123456Z"
}
```

## Status Values

### Job Status
- `queued`: Job is queued and waiting to start
- `running`: Job is currently executing
- `completed`: Job finished successfully
- `failed`: Job failed with an error
- `cancelled`: Job was cancelled

### Terminal States
Jobs with status `completed`, `failed`, or `cancelled` are considered terminal and will not change.

## Progress Tracking

### Progress Percentages
- Range: 0-100
- `null` when not available
- Updated in real-time as collectors report progress

### Messages
- Human-readable status messages
- Updated throughout the collection process
- Examples: "Starting API connection...", "Processing devices...", "Saving to database..."

### Duration
- `duration_seconds`: Total runtime in seconds (only available for terminal jobs)
- `duration`: Human-readable format (e.g., "2m 15s")

## Polling Guidelines

### Recommended Polling
- **Interval**: 5-10 seconds
- **Backoff**: Stop polling when job reaches terminal state
- **Timeout**: Stop polling after 60 seconds of no progress updates

### Rate Limits
- **Limit**: 60 requests per minute per client
- **Scope**: Applies to `/api/collectors/runs/*` and `/api/collectors/history` endpoints

## Timezone Handling

All timestamps are in UTC with 'Z' suffix:
- Format: `YYYY-MM-DDTHH:mm:ss.ssssssZ`
- Example: `2025-10-06T15:16:10.552780Z`
- Dashboard should convert to local timezone for display

## Error Handling

### HTTP Status Codes
- `200`: Success
- `201`: Created (for POST /api/collectors/run)
- `404`: Batch/Job not found
- `500`: Internal server error

### Error Response Format
```json
{
  "error": "Job not found"
}
```

## Integration Examples

### Frontend Polling Pattern
```javascript
async function pollBatchStatus(batchId) {
  const response = await fetch(`/api/collectors/runs/batch/${batchId}`);
  const data = await response.json();
  
  if (data.status === 'completed' || data.status === 'failed') {
    // Stop polling - job is terminal
    return data;
  }
  
  // Continue polling
  setTimeout(() => pollBatchStatus(batchId), 5000);
}
```

### Progress Update Integration
Collectors can update their progress using the `progress_tracker.py` utility:

```python
from api.progress_tracker import update_job_progress

# Update job progress
update_job_progress(job_id, 'running', 50, 'Processing devices...')

# Complete job
update_job_progress(job_id, 'completed', 100, 'Collection completed')
```

## Security

### Authentication
- **Method**: API key header `X-API-Key` (to be provisioned)
- **Alternative**: JWT Bearer token `Authorization: Bearer <token>`
- **CSRF**: Not required for token-based authentication

### CORS
- **Allowed Origins**: `https://dashboards.enersystems.com`, `http://localhost:3000`, `http://localhost:8080`
- **Methods**: GET, POST, PUT, DELETE, OPTIONS
- **Headers**: Content-Type, Authorization, X-Requested-With, X-API-Key, Cache-Control, Pragma
- **Credentials**: true
- **Max Age**: 86400 (24 hours)

## Webhook Support (Optional)

Future enhancement for real-time notifications:

**Webhook Payload:**
```json
{
  "batch_id": "bc_12345678",
  "status": "completed",
  "collectors": [...],
  "timestamp": "2025-10-06T15:17:30.123456Z"
}
```

**Headers:**
- `X-Signature`: HMAC-SHA256 signature for verification
- `Content-Type`: application/json

## Database Schema

### Tables
- `job_batches`: Batch-level tracking
- `job_runs`: Individual job tracking

### Key Fields
- `batch_id`, `job_id`: Unique identifiers
- `status`: Current status
- `progress_percent`: 0-100 progress
- `started_at`, `ended_at`: Timestamps
- `duration_seconds`: Calculated runtime
- `message`, `error`: Status information

## Documentation Endpoints

The API server also provides documentation endpoints for easy access:

- **GET** `/api/docs` - Documentation index
- **GET** `/api/docs/DASHBOARD_AI_COLLECTOR_TRACKING_GUIDE.md` - Complete integration guide
- **GET** `/api/docs/DASHBOARD_AI_PROMPT.md` - Quick start guide
- **GET** `/api/docs/COLLECTOR_RUN_TRACKING_API.md` - Full API reference

These endpoints serve the documentation files directly from the API server, making them accessible over the network for Dashboard AI and other integrations.

## Migration Notes

This API extends the existing collector system:
- **Backward Compatible**: Existing endpoints continue to work
- **Enhanced History**: `/api/collectors/history` now includes job IDs and progress
- **New Tracking**: Batch and job-level progress monitoring
- **Real-time Updates**: Live progress reporting during collection

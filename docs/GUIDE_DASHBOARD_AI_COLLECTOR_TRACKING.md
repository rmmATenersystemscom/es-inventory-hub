# Dashboard AI: Collector Run Tracking Integration Guide

**Last Updated**: October 9, 2025  
**ES Inventory Hub Version**: v1.19.5  
**Status**: ✅ **FULLY OPERATIONAL**

> **🔧 API Fix (October 9, 2025)**: Fixed collector execution logic to properly handle only actual collectors (ninja, threatlocker) and prevent execution of non-existent collector types. The API now correctly filters collector execution and provides proper error handling.

## Overview

The ES Inventory Hub now provides real-time collector run tracking with progress monitoring. This guide explains how Dashboard AI can integrate with the new tracking system to provide a responsive user experience.

## Quick Start

### 1. Trigger Collector Run
```javascript
// POST to trigger collectors
const response = await fetch('https://db-api.enersystems.com:5400/api/collectors/run', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key-here' // When available
  },
  body: JSON.stringify({
    collectors: ['ninja', 'threatlocker'],
    priority: 'normal',
    run_cross_vendor: true
  })
});

const data = await response.json();
// Returns: { batch_id: "bc_12345678", collectors: [...] }
```

### 2. Poll for Progress
```javascript
// Poll batch status every 5-10 seconds
async function pollBatchStatus(batchId) {
  const response = await fetch(`https://db-api.enersystems.com:5400/api/collectors/runs/batch/${batchId}`);
  const data = await response.json();
  
  // Check if batch is complete
  if (data.status === 'completed' || data.status === 'failed') {
    return data; // Stop polling
  }
  
  // Continue polling
  setTimeout(() => pollBatchStatus(batchId), 5000);
}
```

## API Endpoints

### POST /api/collectors/run
**Purpose**: Trigger collector runs and get tracking IDs

**Request**:
```json
{
  "collectors": ["ninja", "threatlocker"],
  "priority": "normal",
  "run_cross_vendor": true
}
```

**Parameters**:
- `collectors` (array): List of collectors to run
- `priority` (string): Job priority - default: `normal`
- `run_cross_vendor` (boolean): Include cross-vendor checks - default: `true`

**Note**: The endpoint automatically includes Windows 11 24H2 assessment.

**Response** (201):
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
    },
    {
      "job_name": "cross-vendor-checks",
      "job_id": "cv_99887766",
      "status": "queued",
      "started_at": "2025-10-06T15:16:10.552780Z"
    },
    {
      "job_name": "windows-11-24h2-assessment",
      "job_id": "w24_55443322",
      "status": "queued",
      "started_at": "2025-10-06T15:16:10.552780Z"
    }
  ]
}
```

### GET /api/collectors/runs/batch/{batch_id}
**Purpose**: Get real-time batch status with all jobs

**Response**:
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
  "collectors": [
    {
      "job_name": "ninja-collector",
      "job_id": "ni_87654321",
      "status": "running",
      "progress_percent": 70,
      "message": "Processing page 7/10",
      "started_at": "2025-10-06T15:16:10.552780Z",
      "updated_at": "2025-10-06T15:16:45.123456Z",
      "ended_at": null,
      "duration_seconds": null
    }
  ],
  "duration_seconds": null
}
```

### GET /api/collectors/runs/job/{job_id}
**Purpose**: Get individual job status

### GET /api/collectors/runs/latest?collectors=ninja,threatlocker
**Purpose**: Get latest active or most recent terminal runs

### GET /api/collectors/history?limit=10
**Purpose**: Get run history including running jobs

## Status Values

### Job Status
- `queued`: Job is queued and waiting to start
- `running`: Job is currently executing
- `completed`: Job finished successfully
- `failed`: Job failed with an error
- `cancelled`: Job was cancelled

### Terminal States
Jobs with status `completed`, `failed`, or `cancelled` are terminal and will not change.

## Implementation Patterns

### 1. Basic Polling Pattern
```javascript
class CollectorTracker {
  constructor() {
    this.pollInterval = 5000; // 5 seconds
    this.maxPollTime = 300000; // 5 minutes
  }
  
  async startTracking(batchId) {
    const startTime = Date.now();
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/collectors/runs/batch/${batchId}`);
        const data = await response.json();
        
        // Update UI with progress
        this.updateProgress(data);
        
        // Check if complete
        if (this.isTerminal(data.status)) {
          this.onComplete(data);
          return;
        }
        
        // Check timeout
        if (Date.now() - startTime > this.maxPollTime) {
          this.onTimeout();
          return;
        }
        
        // Continue polling
        setTimeout(poll, this.pollInterval);
      } catch (error) {
        this.onError(error);
      }
    };
    
    poll();
  }
  
  isTerminal(status) {
    return ['completed', 'failed', 'cancelled'].includes(status);
  }
  
  updateProgress(data) {
    // Update progress bars, status messages, etc.
    console.log(`Batch ${data.batch_id}: ${data.status} (${data.progress_percent}%)`);
    
    data.collectors.forEach(job => {
      console.log(`  ${job.job_name}: ${job.status} (${job.progress_percent}%) - ${job.message}`);
    });
  }
}
```

### 2. React Hook Pattern
```javascript
import { useState, useEffect } from 'react';

function useCollectorTracking(batchId) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    if (!batchId) return;
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/collectors/runs/batch/${batchId}`);
        const data = await response.json();
        
        setStatus(data);
        setLoading(false);
        
        // Stop polling if terminal
        if (['completed', 'failed', 'cancelled'].includes(data.status)) {
          return;
        }
        
        // Continue polling
        setTimeout(poll, 5000);
      } catch (err) {
        setError(err);
        setLoading(false);
      }
    };
    
    poll();
  }, [batchId]);
  
  return { status, loading, error };
}
```

### 3. Vue.js Composable Pattern
```javascript
import { ref, onMounted, onUnmounted } from 'vue';

export function useCollectorTracking(batchId) {
  const status = ref(null);
  const loading = ref(true);
  const error = ref(null);
  let pollTimer = null;
  
  const poll = async () => {
    try {
      const response = await fetch(`/api/collectors/runs/batch/${batchId}`);
      const data = await response.json();
      
      status.value = data;
      loading.value = false;
      
      // Stop polling if terminal
      if (['completed', 'failed', 'cancelled'].includes(data.status)) {
        return;
      }
      
      // Continue polling
      pollTimer = setTimeout(poll, 5000);
    } catch (err) {
      error.value = err;
      loading.value = false;
    }
  };
  
  onMounted(() => {
    if (batchId) poll();
  });
  
  onUnmounted(() => {
    if (pollTimer) clearTimeout(pollTimer);
  });
  
  return { status, loading, error };
}
```

## UI Components

### Progress Display
```javascript
function CollectorProgress({ batchId }) {
  const { status, loading, error } = useCollectorTracking(batchId);
  
  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;
  if (!status) return <div>No status available</div>;
  
  return (
    <div className="collector-progress">
      <h3>Batch {batchId}</h3>
      <div className="batch-status">
        Status: {status.status} ({status.progress_percent}%)
      </div>
      
      {status.collectors.map(job => (
        <div key={job.job_id} className="job-progress">
          <h4>{job.job_name}</h4>
          <div className="progress-bar">
            <div 
              className="progress-fill" 
              style={{ width: `${job.progress_percent || 0}%` }}
            />
          </div>
          <div className="job-message">{job.message}</div>
        </div>
      ))}
    </div>
  );
}
```

## Error Handling

### Common Error Scenarios
1. **Network errors**: Retry with exponential backoff
2. **API errors**: Check HTTP status codes
3. **Timeout**: Stop polling after reasonable time
4. **Invalid batch ID**: Handle 404 responses

### Error Response Format
```json
{
  "error": "Batch not found"
}
```

## Performance Considerations

### Polling Guidelines
- **Interval**: 5-10 seconds (not more frequent)
- **Timeout**: Stop after 5-10 minutes
- **Backoff**: Increase interval if no progress updates
- **Rate Limits**: 60 requests/minute per client

### Optimization Tips
1. **Stop polling** when jobs reach terminal state
2. **Cache responses** briefly to avoid duplicate requests
3. **Use WebSocket** if available for real-time updates
4. **Batch requests** when checking multiple jobs

## Security

### Authentication
- **API Key**: Include `X-API-Key` header when available
- **CORS**: Configured for `https://dashboards.enersystems.com` with full header support
- **HTTPS**: All endpoints require HTTPS

### Best Practices
1. **Validate responses** before processing
2. **Sanitize data** before displaying
3. **Handle errors gracefully**
4. **Don't expose sensitive information**

## Testing

### Test Scenarios
1. **Happy path**: Successful collector run
2. **Failure case**: Collector fails with error
3. **Timeout case**: Long-running job
4. **Network issues**: Connection problems

### Mock Data
```javascript
const mockBatchStatus = {
  batch_id: "bc_test123",
  status: "running",
  progress_percent: 50,
  collectors: [
    {
      job_name: "ninja-collector",
      job_id: "ni_test123",
      status: "running",
      progress_percent: 60,
      message: "Processing devices..."
    }
  ]
};
```

## Migration from Old System

### Before (Old System)
```javascript
// Old way - no progress tracking
fetch('/api/collectors/run', { method: 'POST' })
  .then(() => {
    // Show generic "Running..." message
    // No way to track progress or completion
  });
```

### After (New System)
```javascript
// New way - full progress tracking with complete sequence
const response = await fetch('/api/collectors/run', { 
  method: 'POST',
  body: JSON.stringify({ 
    collectors: ['ninja', 'threatlocker'],
    run_cross_vendor: true  // Includes cross-vendor checks + Windows 11 24H2 assessment
  })
});
const { batch_id } = await response.json();

// Track progress with real-time updates
const tracker = new CollectorTracker();
tracker.startTracking(batch_id);
```

## Troubleshooting

### Common Issues
1. **Jobs stuck in "queued"**: Check if services are running
2. **No progress updates**: Verify API endpoints are working
3. **Polling too frequent**: Increase interval to 10+ seconds
4. **CORS errors**: Ensure proper domain configuration

### Debug Tools
- **Browser DevTools**: Network tab for API calls
- **Console logs**: Check for JavaScript errors
- **API testing**: Use curl or Postman to test endpoints

## Support

For technical support or questions about the collector tracking system:
- **Documentation**: `/docs/API_COLLECTOR_RUN_TRACKING.md`
- **API Reference**: Full endpoint documentation
- **Examples**: Working code samples and patterns

# Dashboard AI Integration Prompt

## Quick Integration Guide for Dashboard AI

The ES Inventory Hub now provides **real-time collector run tracking** with progress monitoring. Here's how to integrate it into your dashboard:

### 🚀 Quick Start

**1. Trigger Collectors:**
```javascript
const response = await fetch('https://db-api.enersystems.com:5400/api/collectors/run', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ collectors: ['ninja', 'threatlocker'] })
});
const { batch_id } = await response.json();
```

**2. Poll for Progress:**
```javascript
const pollStatus = async (batchId) => {
  const response = await fetch(`https://db-api.enersystems.com:5400/api/collectors/runs/batch/${batchId}`);
  const data = await response.json();
  
  // Update UI with real-time progress
  updateProgressUI(data);
  
  // Stop polling when complete
  if (['completed', 'failed', 'cancelled'].includes(data.status)) {
    return;
  }
  
  // Continue polling every 5-10 seconds
  setTimeout(() => pollStatus(batchId), 5000);
};
```

### 📊 What You Get

- **Real-time progress**: Live updates with percentages and messages
- **Individual job tracking**: Monitor each collector separately  
- **Completion signals**: Know exactly when jobs finish
- **Error handling**: Clear error messages and failure reasons
- **Duration tracking**: How long each job took to complete

### 🎯 Key Endpoints

- `POST /api/collectors/run` - Start collectors, get batch ID
- `GET /api/collectors/runs/batch/{batch_id}` - Poll for progress
- `GET /api/collectors/runs/job/{job_id}` - Individual job status
- `GET /api/collectors/runs/latest` - Latest runs
- `GET /api/collectors/history` - Run history

### 💡 Implementation Tips

1. **Poll every 5-10 seconds** (not more frequent)
2. **Stop polling** when status is `completed`, `failed`, or `cancelled`
3. **Show progress bars** using `progress_percent` field
4. **Display messages** using `message` field for user feedback
5. **Handle errors gracefully** - check for `error` field

### 🔧 Example UI Update

```javascript
function updateProgressUI(data) {
  // Update batch status
  document.getElementById('batch-status').textContent = 
    `${data.status} (${data.progress_percent}%)`;
  
  // Update individual jobs
  data.collectors.forEach(job => {
    const jobElement = document.getElementById(`job-${job.job_id}`);
    jobElement.querySelector('.progress').style.width = `${job.progress_percent}%`;
    jobElement.querySelector('.message').textContent = job.message;
  });
}
```

### 📚 Full Documentation

See `/docs/DASHBOARD_AI_COLLECTOR_TRACKING_GUIDE.md` for complete integration guide with React/Vue examples, error handling, and advanced patterns.

### 🎉 Benefits

- **No more generic "Running..." messages**
- **Real progress bars** showing actual completion percentage
- **Live status messages** like "Processing devices..." or "Saving to database..."
- **Exact completion times** and duration tracking
- **Clear error reporting** when things go wrong
- **Professional UX** that users will love

This replaces the old system where you had to guess if collectors were running. Now you get **real-time visibility** into exactly what's happening!

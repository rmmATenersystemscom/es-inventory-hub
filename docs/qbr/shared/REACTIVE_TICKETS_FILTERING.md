# Reactive Tickets Filtering and Time Calculation

## Overview

This document explains how **reactive tickets** are defined and filtered in the ES Dashboards project, and how time spent on reactive tickets is calculated **by month**. This information is based on the **SMARTNUMBERS** dashboard implementation, which tracks reactive ticket metrics (created, closed, and time spent) across the last 13 months.

For general ConnectWise API integration patterns and authentication, see [API_CONNECTWISE.md](../../../../docs/API_CONNECTWISE.md).

---

## Definition of Reactive Tickets

**Reactive tickets** are defined as tickets that meet ALL of the following criteria:

1. **Board**: Must be on the "Help Desk" board
2. **Parent Tickets Only**: Must be parent tickets (exclude child tickets)

**Note**: Unlike some other dashboards, the SMARTNUMBERS dashboard does NOT filter by status when counting tickets created or closed. It tracks all Help Desk tickets regardless of status, then filters closed tickets by status when querying closed dates.

### Exact Filter Criteria

The ConnectWise API conditions used to filter reactive tickets vary by use case:

**For Tickets Created**:
```
board/name="Help Desk" AND parentTicketId = null
```
Filtered by `dateEntered` within the month range.

**For Tickets Closed**:
```
board/name="Help Desk" AND parentTicketId = null AND status/name IN (">Closed",">Closed - No response","Closed")
```
Filtered by `closedDate` within the month range.

**For Open Tickets** (used in other dashboards):
```
board/name="Help Desk" AND status/name!=">Closed" AND status/name!=">Closed - No response" AND parentTicketId = null
```

---

## SMARTNUMBERS Dashboard: Monthly Tracking

The SMARTNUMBERS dashboard tracks reactive tickets **by month** for the last 13 months, providing three key metrics:

1. **Tickets Created** - Count of Help Desk tickets created each month
2. **Tickets Closed** - Count of Help Desk tickets closed each month
3. **Time Spent** - Total hours spent on Help Desk tickets each month

### Timezone-Aware Month Ranges

The SMARTNUMBERS dashboard uses **timezone-aware month ranges** to ensure accurate monthly aggregations based on the user's local timezone. This is critical because:

- Users may be in different timezones
- Month boundaries must align with the user's local calendar
- Time entries are recorded in UTC but need to be grouped by local month

**Implementation**: Uses centralized timezone utilities from `utils/date_handling.py`:
- `utc_spans_for_last_n_months()` - Gets UTC date ranges for the last N months in user's timezone
- `get_connectwise_month_range()` - Gets ConnectWise API-formatted date strings for a specific month
- `format_date_range_for_connectwise_api()` - Formats UTC date ranges for ConnectWise API queries

---

## Tracking Tickets Created by Month

### Implementation

```python
def get_tickets_created_for_month(year, month, user_timezone='UTC'):
    """Return the count of tickets created in a specific month using timezone-aware approach on the 'Help Desk' board only."""
    headers = get_auth_headers()
    
    # Use local timezone utilities
    from utils.date_handling import get_connectwise_month_range
    start_str, end_str = get_connectwise_month_range(user_timezone, year, month)
    
    page = 1
    page_size = 250
    total = 0
    while True:
        conditions = f'dateEntered>=[{start_str}] AND dateEntered<=[{end_str}] AND board/name="Help Desk" AND parentTicketId = null'
        params = {
            'conditions': conditions,
            'fields': 'id,dateEntered,board/name,_info',
            'pageSize': page_size,
            'page': page
        }
        session, timeout = _effective_session_timeout()
        response = session.get(TICKETS_ENDPOINT, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        tickets = response.json()
        total += len(tickets)
        if len(tickets) < page_size:
            break
        page += 1
    return total
```

### Key Points

- **Filter**: `board/name="Help Desk" AND parentTicketId = null`
- **Date Field**: Uses `dateEntered` to filter by creation date
- **No Status Filter**: Counts all tickets created, regardless of current status
- **Timezone-Aware**: Month boundaries are calculated based on user's timezone
- **Pagination**: Handles multiple pages of results

### Last 13 Months Implementation

```python
def get_tickets_created_last_12_months(user_timezone='UTC'):
    """Get tickets created in the last 13 months using centralized timezone handling"""
    from utils.date_handling import utc_spans_for_last_n_months
    
    # Get UTC spans for the last 13 months with labels
    spans = utc_spans_for_last_n_months(user_timezone, 13)
    
    data = []
    labels = []
    
    # Process each month
    for start_utc, end_utc, month_label in spans:
        year = start_utc.year
        month = start_utc.month
        
        # Handle year rollover for December
        if start_utc.month == 12 and end_utc.month == 1:
            year = start_utc.year
            month = 12
        
        count = get_tickets_created_for_month(year, month, user_timezone)
        data.append(count)
        labels.append(month_label)
    
    return data, labels
```

**Reference**: See `get_tickets_created_for_month()` and `get_tickets_created_last_12_months()` in `connectwise_api.py` (lines 68-145).

---

## Tracking Tickets Closed by Month

### Implementation

```python
def get_tickets_closed_for_month(year, month, user_timezone='UTC'):
    """Return the count of tickets closed in a specific month using timezone-aware approach on the 'Help Desk' board only."""
    headers = get_auth_headers()
    
    # Use local timezone utilities
    from utils.date_handling import get_connectwise_month_range
    start_str, end_str = get_connectwise_month_range(user_timezone, year, month)
    
    page = 1
    page_size = 250
    total = 0
    while True:
        conditions = (
            f'status/name IN (">Closed",">Closed - No response","Closed") '
            f'AND closedDate>=[{start_str}] AND closedDate<=[{end_str}] '
            f'AND board/name="Help Desk" AND parentTicketId = null'
        )
        params = {
            'conditions': conditions,
            'fields': 'id,closedDate,board/name',
            'pageSize': page_size,
            'page': page
        }
        session, timeout = _effective_session_timeout()
        response = session.get(TICKETS_ENDPOINT, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        tickets = response.json()
        total += len(tickets)
        if len(tickets) < page_size:
            break
        page += 1
    return total
```

### Key Points

- **Filter**: `board/name="Help Desk" AND parentTicketId = null AND status/name IN (">Closed",">Closed - No response","Closed")`
- **Date Field**: Uses `closedDate` to filter by closure date
- **Status Filter**: Only counts tickets with closed statuses
- **Timezone-Aware**: Month boundaries are calculated based on user's timezone
- **Pagination**: Handles multiple pages of results

### Last 13 Months Implementation

```python
def get_tickets_closed_last_12_months(user_timezone='UTC'):
    """Return the count of tickets closed in the last 13 months using centralized timezone handling"""
    from utils.date_handling import utc_spans_for_last_n_months
    
    # Get UTC spans for the last 13 months with labels
    spans = utc_spans_for_last_n_months(user_timezone, 13)
    
    data = []
    labels = []
    
    # Process each month
    for start_utc, end_utc, month_label in spans:
        year = start_utc.year
        month = start_utc.month
        
        # Handle year rollover for December
        if start_utc.month == 12 and end_utc.month == 1:
            year = start_utc.year
            month = 12
        
        count = get_tickets_closed_for_month(year, month, user_timezone)
        data.append(count)
        labels.append(month_label)
    
    return data, labels
```

**Reference**: See `get_tickets_closed_for_month()` and `get_tickets_closed_last_12_months()` in `connectwise_api.py` (lines 225-298).

---

## Calculating Time Spent on Reactive Tickets by Month

Calculating time spent on reactive tickets requires a multi-step process because:

1. Time entries are linked to tickets by ticket ID, not by board
2. We need to filter time entries to only those associated with Help Desk tickets
3. The ConnectWise API has URL length limits, requiring batch processing
4. Time entries must be grouped by month based on when they were entered

### Step-by-Step Process

#### Step 1: Get All Time Entries for Date Range

Query the time entries endpoint for all time entries in the specified date range where `chargeToType="ServiceTicket"`:

```python
conditions = f'dateEntered>=[{start_str}] AND dateEntered<=[{end_str}] AND chargeToType="ServiceTicket"'
params = {
    'conditions': conditions,
    'fields': 'id,actualHours,dateEntered,chargeToId,_info',
    'pageSize': page_size,
    'page': page
}
response = session.get(time_entries_endpoint, headers=headers, params=params, timeout=timeout)
time_entries = response.json()
```

**Note**: 
- This gets ALL time entries for ALL service tickets, not just Help Desk tickets
- Uses `dateEntered` on the time entry (when time was logged), not the ticket date
- The date range corresponds to the month being calculated

#### Step 2: Extract Unique Ticket IDs

From the time entries, extract the unique ticket IDs:

```python
ticket_ids = set()
for entry in all_time_entries:
    charge_to_id = entry.get('chargeToId')
    if charge_to_id:
        ticket_ids.add(charge_to_id)
```

#### Step 3: Query Tickets in Batches to Identify Help Desk Tickets

Due to ConnectWise API URL length limits, query tickets in small batches (typically 20 tickets per batch):

```python
ticket_batch_size = 20
help_desk_ticket_ids = set()
ticket_id_list = list(ticket_ids)
total_batches = (len(ticket_id_list) + ticket_batch_size - 1) // ticket_batch_size

for batch_num in range(total_batches):
    start_idx = batch_num * ticket_batch_size
    end_idx = min(start_idx + ticket_batch_size, len(ticket_id_list))
    batch_ticket_ids = ticket_id_list[start_idx:end_idx]
    
    # Create conditions for this batch
    id_conditions = ' OR '.join([f'id={ticket_id}' for ticket_id in batch_ticket_ids])
    conditions = f'({id_conditions}) AND board/name="Help Desk"'
    
    params = {
        'conditions': conditions,
        'fields': 'id,board/name',
        'pageSize': ticket_batch_size,
        'page': 1
    }
    
    response = session.get(tickets_endpoint, headers=headers, params=params, timeout=timeout)
    tickets = response.json()
    
    for ticket in tickets:
        help_desk_ticket_ids.add(ticket.get('id'))
```

**Important**: Batch size of 20 is used to avoid URL length limits. See [API_CONNECTWISE.md](../../../../docs/API_CONNECTWISE.md#url-length-limits) for details.

#### Step 4: Sum Hours Only for Help Desk Tickets

Finally, sum the `actualHours` only for time entries that belong to Help Desk tickets:

```python
total_hours = 0.0
for entry in all_time_entries:
    charge_to_id = entry.get('chargeToId')
    if charge_to_id and charge_to_id in help_desk_ticket_ids:
        hours = entry.get('actualHours', 0)
        if hours:
            try:
                total_hours += float(hours)
            except (ValueError, TypeError):
                continue
```

### Complete Implementation Example

```python
def get_total_time_for_date_range(start_str: str, end_str: str) -> float:
    """Return the total time spent on Help Desk tickets for a specific date range in hours."""
    headers = get_auth_headers()
    time_entries_endpoint = f'{BASE_URI}/time/entries'
    
    # Step 1: Get all time entries for date range
    all_time_entries = []
    page = 1
    page_size = 250
    
    while True:
        conditions = f'dateEntered>=[{start_str}] AND dateEntered<=[{end_str}] AND chargeToType="ServiceTicket"'
        params = {
            'conditions': conditions,
            'fields': 'id,actualHours,dateEntered,chargeToId,_info',
            'pageSize': page_size,
            'page': page
        }
        session, timeout = _effective_session_timeout()
        response = session.get(time_entries_endpoint, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        time_entries = response.json()
        all_time_entries.extend(time_entries)
        
        if len(time_entries) < page_size:
            break
        page += 1
    
    if not all_time_entries:
        return 0.0
    
    # Step 2: Extract unique ticket IDs
    ticket_ids = set()
    for entry in all_time_entries:
        charge_to_id = entry.get('chargeToId')
        if charge_to_id:
            ticket_ids.add(charge_to_id)
    
    # Step 3: Query tickets in batches to identify Help Desk tickets
    tickets_endpoint = f'{BASE_URI}/service/tickets'
    help_desk_ticket_ids = set()
    ticket_batch_size = 20
    ticket_id_list = list(ticket_ids)
    total_batches = (len(ticket_id_list) + ticket_batch_size - 1) // ticket_batch_size
    
    for batch_num in range(total_batches):
        start_idx = batch_num * ticket_batch_size
        end_idx = min(start_idx + ticket_batch_size, len(ticket_id_list))
        batch_ticket_ids = ticket_id_list[start_idx:end_idx]
        
        id_conditions = ' OR '.join([f'id={ticket_id}' for ticket_id in batch_ticket_ids])
        conditions = f'({id_conditions}) AND board/name="Help Desk"'
        
        params = {
            'conditions': conditions,
            'fields': 'id,board/name',
            'pageSize': ticket_batch_size,
            'page': 1
        }
        
        response = session.get(tickets_endpoint, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        tickets = response.json()
        
        for ticket in tickets:
            help_desk_ticket_ids.add(ticket.get('id'))
    
    # Step 4: Sum hours only for Help Desk tickets
    total_hours = 0.0
    for entry in all_time_entries:
        charge_to_id = entry.get('chargeToId')
        if charge_to_id and charge_to_id in help_desk_ticket_ids:
            hours = entry.get('actualHours', 0)
            if hours:
                try:
                    total_hours += float(hours)
                except (ValueError, TypeError):
                    continue
    
    return total_hours
```

### Last 13 Months Implementation

```python
def get_total_time_last_12_months(user_timezone='UTC'):
    """Return the total time spent on Help Desk tickets for the last 13 months using centralized timezone handling in hours."""
    from utils.date_handling import utc_spans_for_last_n_months, format_date_range_for_connectwise_api
    
    # Get UTC spans for the last 13 months
    spans = utc_spans_for_last_n_months(user_timezone, 13)
    
    data = []
    labels = []
    
    # Process each month
    for start_utc, end_utc, month_label in spans:
        start_str, end_str = format_date_range_for_connectwise_api(start_utc, end_utc)
        
        # Get time entries for this month
        hours = get_total_time_for_date_range(start_str, end_str)
        
        data.append(hours)
        labels.append(month_label)
    
    return data, labels
```

**Reference**: See `get_total_time_for_date_range()` and `get_total_time_last_12_months()` in `connectwise_api.py` (lines 300-436).

---

## Key Considerations

### Timezone-Aware Month Boundaries

The SMARTNUMBERS dashboard uses timezone-aware month boundaries to ensure accurate monthly aggregations:

- **User Timezone**: Month boundaries are calculated based on the user's local timezone
- **UTC Conversion**: Local month boundaries are converted to UTC for API queries
- **Month Labels**: Labels reflect the month name in the user's timezone (e.g., "Jan 2024", "Feb 2024")
- **Year Rollover**: Handles December-to-January transitions correctly

**Implementation**: Uses `utc_spans_for_last_n_months()` from `utils/date_handling.py` which:
- Takes user timezone and number of months
- Returns list of (start_utc, end_utc, month_label) tuples
- Handles timezone conversions and month boundary calculations

### URL Length Limits

The ConnectWise API has URL length limits. When querying many ticket IDs, use small batches (typically 20 tickets per batch) to avoid exceeding these limits.

**See**: [API_CONNECTWISE.md](../../../../docs/API_CONNECTWISE.md#url-length-limits) for more details.

### Pagination

Both ticket queries and time entry queries use pagination. Always handle multiple pages:

```python
while True:
    # ... make request ...
    results = response.json()
    all_results.extend(results)
    
    if len(results) < page_size:
        break
    page += 1
```

**See**: [API_CONNECTWISE.md](../../../../docs/API_CONNECTWISE.md#pagination) for pagination patterns.

### Date Formatting

Dates must be formatted in ISO 8601 format with brackets for ConnectWise API:

```python
# Format: YYYY-MM-DDTHH:MM:SSZ
start_str = "2024-01-01T00:00:00Z"
end_str = "2024-01-31T23:59:59Z"

# In conditions:
conditions = f'dateEntered>=[{start_str}] AND dateEntered<=[{end_str}]'
```

**See**: [API_CONNECTWISE.md](../../../../docs/API_CONNECTWISE.md#date-formatting) for date formatting details.

### Performance Considerations

1. **Batch Size**: Use batch size of 20 for ticket queries to avoid URL length limits
2. **Page Size**: Use page size of 250 for time entry queries (maximum allowed)
3. **Timeout**: Use appropriate timeouts (30-120 seconds) for complex queries
4. **Error Handling**: Continue processing even if individual batches fail
5. **Month-by-Month Processing**: Process each month separately to avoid memory issues with large datasets

---

## Usage in SMARTNUMBERS Dashboard

The SMARTNUMBERS dashboard uses reactive ticket filtering to:

1. **Track Tickets Created**: Count of Help Desk tickets created each month (last 13 months)
2. **Track Tickets Closed**: Count of Help Desk tickets closed each month (last 13 months)
3. **Track Time Spent**: Total hours spent on Help Desk tickets each month (last 13 months)

### Dashboard Features

- **Timezone-Aware**: All metrics respect user's local timezone
- **13-Month View**: Shows last 13 months of data for trend analysis
- **Dual Charts**: 
  - Bar chart showing created vs closed tickets
  - Bar chart showing hours spent per month
- **Real-Time Data**: Data loaded via JavaScript API calls with timezone support

**Reference**: See `app.py` and `connectwise_api.py` in this directory.

---

## Related Documentation

- [API_CONNECTWISE.md](../../../../docs/API_CONNECTWISE.md) - ConnectWise API integration patterns and authentication
- [STD_BUSINESS_LOGIC.md](../../../../docs/STD_BUSINESS_LOGIC.md) - Business logic standards including reactive ticket definitions
- `utils/date_handling.py` - Timezone-aware date handling utilities

---

## Summary

**Reactive Tickets Definition**:
- Board: "Help Desk"
- Parent tickets only (`parentTicketId = null`)
- Status filter varies by use case (created vs closed)

**SMARTNUMBERS Monthly Tracking**:

1. **Tickets Created**:
   - Filter: `board/name="Help Desk" AND parentTicketId = null`
   - Date field: `dateEntered`
   - No status filter

2. **Tickets Closed**:
   - Filter: `board/name="Help Desk" AND parentTicketId = null AND status/name IN (">Closed",">Closed - No response","Closed")`
   - Date field: `closedDate`

3. **Time Spent**:
   - Get all time entries for month (chargeToType="ServiceTicket", filtered by time entry `dateEntered`)
   - Extract ticket IDs from time entries
   - Query tickets in batches (20 per batch) to identify Help Desk tickets
   - Sum `actualHours` only for Help Desk tickets

**Key Implementation Files**:
- `connectwise_api.py` (this directory) - Main implementation
- `utils/date_handling.py` - Timezone-aware date utilities

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-27  
**Maintainer**: ES Dashboards Team


"""
Variance Management Integration for Collectors

This module provides functions to integrate variance status management
with the collector workflow, ensuring that manual fixes are properly
tracked and verified.
"""

from datetime import date, datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from storage.schema import Exceptions


def reset_variance_status(session: Session, snapshot_date: date) -> int:
    """
    Reset variance status before new data collection.
    
    This function should be called at the start of collector runs to
    reset manually fixed exceptions back to 'active' status so they
    can be re-evaluated with fresh data.
    
    Args:
        session: Database session
        snapshot_date: Date of the new snapshot
        
    Returns:
        int: Number of exceptions reset
    """
    query = text("""
        UPDATE exceptions 
        SET variance_status = 'active' 
        WHERE date_found = :snapshot_date 
        AND variance_status IN ('manually_fixed', 'stale')
    """)
    
    result = session.execute(query, {'snapshot_date': snapshot_date})
    session.commit()
    
    return result.rowcount


def verify_manual_fixes(session: Session, snapshot_date: date) -> Dict[str, int]:
    """
    Verify manually fixed exceptions against new collector data.
    
    This function should be called after collector runs to check if
    manually fixed exceptions are still present in the new data.
    Updates status to 'collector_verified' if fix is confirmed,
    or 'stale' if the issue persists.
    
    Args:
        session: Database session
        snapshot_date: Date of the new snapshot
        
    Returns:
        dict: Count of exceptions by verification status
    """
    # Get all manually fixed exceptions for this date
    manual_fixes_query = text("""
        SELECT 
            e.id,
            e.hostname,
            e.type,
            e.old_value,
            e.new_value,
            e.update_type
        FROM exceptions e
        WHERE e.date_found = :snapshot_date
        AND e.variance_status = 'manually_fixed'
    """)
    
    manual_fixes = session.execute(manual_fixes_query, {'snapshot_date': snapshot_date}).fetchall()
    
    verified_count = 0
    stale_count = 0
    
    for fix in manual_fixes:
        exception_id = fix[0]
        hostname = fix[1]
        exc_type = fix[2]
        old_value = fix[3]
        new_value = fix[4]
        update_type = fix[5]
        
        # Check if the fix is still effective
        is_verified = check_fix_effectiveness(
            session, snapshot_date, hostname, exc_type, 
            old_value, new_value, update_type
        )
        
        if is_verified:
            # Mark as collector verified
            update_query = text("""
                UPDATE exceptions 
                SET variance_status = 'collector_verified'
                WHERE id = :exception_id
            """)
            session.execute(update_query, {'exception_id': exception_id})
            verified_count += 1
        else:
            # Mark as stale (issue persists)
            update_query = text("""
                UPDATE exceptions 
                SET variance_status = 'stale'
                WHERE id = :exception_id
            """)
            session.execute(update_query, {'exception_id': exception_id})
            stale_count += 1
    
    session.commit()
    
    return {
        'verified': verified_count,
        'stale': stale_count,
        'total_checked': len(manual_fixes)
    }


def check_fix_effectiveness(
    session: Session, 
    snapshot_date: date, 
    hostname: str, 
    exc_type: str,
    old_value: Dict[str, Any], 
    new_value: Dict[str, Any], 
    update_type: str
) -> bool:
    """
    Check if a manual fix is still effective against current data.
    
    Args:
        session: Database session
        snapshot_date: Date of the snapshot
        hostname: Device hostname
        exc_type: Exception type
        old_value: Old values before fix
        new_value: New values after fix
        update_type: Type of update performed
        
    Returns:
        bool: True if fix is still effective, False if issue persists
    """
    # This is a simplified check - in practice, you'd want to implement
    # specific logic for each exception type and update type
    
    if exc_type == 'MISSING_NINJA':
        # Check if device now exists in Ninja
        ninja_check = text("""
            SELECT COUNT(*) 
            FROM device_snapshot ds
            JOIN vendor v ON ds.vendor_id = v.id
            WHERE ds.snapshot_date = :snapshot_date
            AND v.name = 'Ninja'
            AND ds.hostname = :hostname
        """)
        
        result = session.execute(ninja_check, {
            'snapshot_date': snapshot_date,
            'hostname': hostname
        }).scalar()
        
        return result > 0
    
    elif exc_type == 'SITE_MISMATCH':
        # Check if site mismatch is resolved
        # Implementation would depend on specific site matching logic
        return True  # Placeholder
    
    elif exc_type == 'SPARE_MISMATCH':
        # Check if spare status is resolved
        # Implementation would depend on specific spare status logic
        return True  # Placeholder
    
    else:
        # Default: assume fix is effective
        return True


def get_variance_status_summary(session: Session, snapshot_date: date) -> Dict[str, Any]:
    """
    Get summary of variance statuses for a given date.
    
    Args:
        session: Database session
        snapshot_date: Date to summarize
        
    Returns:
        dict: Summary of variance statuses
    """
    query = text("""
        SELECT 
            COALESCE(variance_status, 'active') as status,
            type,
            COUNT(*) as count,
            COUNT(CASE WHEN resolved = true THEN 1 END) as resolved_count
        FROM exceptions
        WHERE date_found = :snapshot_date
        GROUP BY variance_status, type
        ORDER BY status, type
    """)
    
    results = session.execute(query, {'snapshot_date': snapshot_date}).fetchall()
    
    summary = {}
    for row in results:
        status = row[0]
        exc_type = row[1]
        count = row[2]
        resolved = row[3]
        
        if status not in summary:
            summary[status] = {}
        
        summary[status][exc_type] = {
            'total': count,
            'resolved': resolved,
            'unresolved': count - resolved
        }
    
    return summary


def cleanup_stale_exceptions(session: Session, days_old: int = 30) -> int:
    """
    Clean up old stale exceptions that haven't been resolved.
    
    Args:
        session: Database session
        days_old: Number of days old to consider for cleanup
        
    Returns:
        int: Number of exceptions cleaned up
    """
    query = text("""
        DELETE FROM exceptions
        WHERE variance_status = 'stale'
        AND date_found < CURRENT_DATE - INTERVAL ':days_old days'
        AND resolved = false
    """)
    
    result = session.execute(query, {'days_old': days_old})
    session.commit()
    
    return result.rowcount


# Integration functions for collector workflow

def pre_collection_variance_reset(session: Session, snapshot_date: date) -> Dict[str, int]:
    """
    Pre-collection variance management.
    
    Call this at the start of collector runs to reset variance statuses.
    
    Args:
        session: Database session
        snapshot_date: Date of the new snapshot
        
    Returns:
        dict: Summary of reset operations
    """
    reset_count = reset_variance_status(session, snapshot_date)
    
    return {
        'exceptions_reset': reset_count,
        'reset_timestamp': datetime.now().isoformat()
    }


def post_collection_variance_verification(session: Session, snapshot_date: date) -> Dict[str, Any]:
    """
    Post-collection variance verification.
    
    Call this after collector runs to verify manual fixes.
    
    Args:
        session: Database session
        snapshot_date: Date of the snapshot
        
    Returns:
        dict: Summary of verification results
    """
    verification_results = verify_manual_fixes(session, snapshot_date)
    status_summary = get_variance_status_summary(session, snapshot_date)
    
    return {
        'verification_results': verification_results,
        'status_summary': status_summary,
        'verification_timestamp': datetime.now().isoformat()
    }

"""
Progress tracking utility for collector runs.
This module provides functions to update job progress in the database.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def get_db_connection():
    """Get database connection using environment variables."""
    db_dsn = os.getenv('DB_DSN')
    if not db_dsn:
        raise ValueError("DB_DSN environment variable not set")
    
    engine = create_engine(db_dsn)
    Session = sessionmaker(bind=engine)
    return Session()

def update_job_progress(job_id, status, progress_percent=None, message=None, error=None):
    """
    Update job progress in the database.
    
    Args:
        job_id (str): The job ID to update
        status (str): New status (queued, running, completed, failed, cancelled)
        progress_percent (int, optional): Progress percentage (0-100)
        message (str, optional): Status message
        error (str, optional): Error message if failed
    """
    try:
        with get_db_connection() as session:
            now = datetime.utcnow()
            
            # Update job run
            job_query = text("""
                UPDATE job_runs 
                SET status = :status, 
                    updated_at = :updated_at,
                    progress_percent = :progress_percent,
                    message = :message,
                    error = :error
                WHERE job_id = :job_id
            """)
            
            session.execute(job_query, {
                'job_id': job_id,
                'status': status,
                'updated_at': now,
                'progress_percent': progress_percent,
                'message': message,
                'error': error
            })
            
            # If job is completed or failed, set ended_at and duration
            if status in ['completed', 'failed', 'cancelled']:
                end_query = text("""
                    UPDATE job_runs 
                    SET ended_at = :ended_at,
                        duration_seconds = EXTRACT(EPOCH FROM (:ended_at - started_at))::INTEGER
                    WHERE job_id = :job_id
                """)
                session.execute(end_query, {
                    'job_id': job_id,
                    'ended_at': now
                })
            
            session.commit()
            print(f"Updated job {job_id}: {status} - {message or ''}")
            
    except Exception as e:
        print(f"Error updating job progress: {e}", file=sys.stderr)

def update_batch_progress(batch_id, status, progress_percent=None, message=None, error=None):
    """
    Update batch progress in the database.
    
    Args:
        batch_id (str): The batch ID to update
        status (str): New status (queued, running, completed, failed, cancelled)
        progress_percent (int, optional): Progress percentage (0-100)
        message (str, optional): Status message
        error (str, optional): Error message if failed
    """
    try:
        with get_db_connection() as session:
            now = datetime.utcnow()
            
            # Update batch
            batch_query = text("""
                UPDATE job_batches 
                SET status = :status, 
                    progress_percent = :progress_percent,
                    message = :message,
                    error = :error
                WHERE batch_id = :batch_id
            """)
            
            session.execute(batch_query, {
                'batch_id': batch_id,
                'status': status,
                'progress_percent': progress_percent,
                'message': message,
                'error': error
            })
            
            # If batch is completed or failed, set ended_at and duration
            if status in ['completed', 'failed', 'cancelled']:
                end_query = text("""
                    UPDATE job_batches 
                    SET ended_at = :ended_at,
                        duration_seconds = EXTRACT(EPOCH FROM (:ended_at - started_at))::INTEGER
                    WHERE batch_id = :batch_id
                """)
                session.execute(end_query, {
                    'batch_id': batch_id,
                    'ended_at': now
                })
            
            session.commit()
            print(f"Updated batch {batch_id}: {status} - {message or ''}")
            
    except Exception as e:
        print(f"Error updating batch progress: {e}", file=sys.stderr)

def get_job_id_by_name(job_name):
    """
    Get the most recent job ID for a given job name.
    This is useful for collectors to find their job ID.
    
    Args:
        job_name (str): The job name (e.g., 'ninja-collector')
        
    Returns:
        str: The job ID, or None if not found
    """
    try:
        with get_db_connection() as session:
            query = text("""
                SELECT job_id 
                FROM job_runs 
                WHERE job_name = :job_name 
                ORDER BY started_at DESC 
                LIMIT 1
            """)
            result = session.execute(query, {'job_name': job_name}).fetchone()
            return result.job_id if result else None
            
    except Exception as e:
        print(f"Error getting job ID: {e}", file=sys.stderr)
        return None

def get_batch_id_by_job_id(job_id):
    """
    Get the batch ID for a given job ID.
    
    Args:
        job_id (str): The job ID
        
    Returns:
        str: The batch ID, or None if not found
    """
    try:
        with get_db_connection() as session:
            query = text("""
                SELECT batch_id 
                FROM job_runs 
                WHERE job_id = :job_id
            """)
            result = session.execute(query, {'job_id': job_id}).fetchone()
            return result.batch_id if result else None
            
    except Exception as e:
        print(f"Error getting batch ID: {e}", file=sys.stderr)
        return None

# Example usage for collectors:
if __name__ == "__main__":
    # Example: Update ninja collector progress
    job_id = get_job_id_by_name('ninja-collector')
    if job_id:
        update_job_progress(job_id, 'running', 25, 'Starting data collection...')
        update_job_progress(job_id, 'running', 50, 'Processing devices...')
        update_job_progress(job_id, 'running', 75, 'Saving to database...')
        update_job_progress(job_id, 'completed', 100, 'Collection completed successfully')

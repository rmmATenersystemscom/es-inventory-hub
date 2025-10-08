"""Job run logging utilities for collectors."""

import uuid
from datetime import datetime
from typing import Optional
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from storage.schema import JobRuns, JobBatches

# Database connection - lazy initialization
from common.config import get_dsn

_engine = None
_Session = None

def get_engine():
    """Get database engine, creating it if necessary."""
    global _engine
    if _engine is None:
        DSN = get_dsn()
        _engine = create_engine(DSN)
    return _engine

def get_session():
    """Get database session."""
    global _Session
    if _Session is None:
        _Session = sessionmaker(bind=get_engine())
    return _Session()


def log_job_start(job_name: str, message: Optional[str] = None) -> str:
    """
    Log the start of a job run.
    
    Args:
        job_name: Name of the job (e.g., 'ninja-collector', 'threatlocker-collector')
        message: Optional message about the job start
        
    Returns:
        str: Job run ID for later completion logging
    """
    with get_session() as session:
        # Create a legacy batch for standalone runs
        batch_id = f"legacy_{uuid.uuid4().hex[:8]}"
        batch = JobBatches(
            batch_id=batch_id,
            status='running',
            started_at=datetime.now(pytz.UTC),
            message=f"Legacy {job_name} run"
        )
        session.add(batch)
        
        # Create job run
        job_id = f"legacy_{uuid.uuid4().hex[:8]}"
        job_run = JobRuns(
            job_id=job_id,
            batch_id=batch_id,
            job_name=job_name,
            started_at=datetime.now(pytz.UTC),
            updated_at=datetime.now(pytz.UTC),
            status='running',
            message=message
        )
        session.add(job_run)
        session.commit()
        return job_id


def log_job_completion(job_run_id: str, status: str = 'completed', message: Optional[str] = None):
    """
    Log the completion of a job run.
    
    Args:
        job_run_id: ID of the job run to complete
        status: Final status ('completed', 'failed')
        message: Optional completion message
    """
    with get_session() as session:
        job_run = session.query(JobRuns).filter_by(job_id=job_run_id).first()
        if job_run:
            job_run.ended_at = datetime.now(pytz.UTC)
            job_run.updated_at = datetime.now(pytz.UTC)
            job_run.status = status
            if message:
                job_run.message = message
            # Calculate duration
            if job_run.started_at and job_run.ended_at:
                duration = job_run.ended_at - job_run.started_at
                job_run.duration_seconds = int(duration.total_seconds())
            session.commit()
            
            # Update batch status if this was the last job in the batch
            batch = session.query(JobBatches).filter_by(batch_id=job_run.batch_id).first()
            if batch:
                remaining_jobs = session.query(JobRuns).filter_by(
                    batch_id=job_run.batch_id, 
                    status='running'
                ).count()
                if remaining_jobs == 0:
                    batch.status = status
                    batch.ended_at = datetime.now(pytz.UTC)
                    if batch.started_at and batch.ended_at:
                        duration = batch.ended_at - batch.started_at
                        batch.duration_seconds = int(duration.total_seconds())
                    session.commit()


def log_job_failure(job_run_id: str, error_message: str):
    """
    Log a job failure.
    
    Args:
        job_run_id: ID of the job run that failed
        error_message: Error message describing the failure
    """
    log_job_completion(job_run_id, status='failed', message=error_message)

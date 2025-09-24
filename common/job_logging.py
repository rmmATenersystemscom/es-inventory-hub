"""Job run logging utilities for collectors."""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from storage.schema import JobRuns

# Database connection
DSN = 'postgresql://postgres:Xat162gT2Qsg4WDlO5r@localhost:5432/es_inventory_hub'
engine = create_engine(DSN)
Session = sessionmaker(bind=engine)

def get_session():
    """Get database session."""
    return Session()


def log_job_start(job_name: str, message: Optional[str] = None) -> int:
    """
    Log the start of a job run.
    
    Args:
        job_name: Name of the job (e.g., 'ninja-collector', 'threatlocker-collector')
        message: Optional message about the job start
        
    Returns:
        int: Job run ID for later completion logging
    """
    with get_session() as session:
        job_run = JobRuns(
            job_name=job_name,
            started_at=datetime.utcnow(),
            status='running',
            message=message
        )
        session.add(job_run)
        session.commit()
        return job_run.id


def log_job_completion(job_run_id: int, status: str = 'completed', message: Optional[str] = None):
    """
    Log the completion of a job run.
    
    Args:
        job_run_id: ID of the job run to complete
        status: Final status ('completed', 'failed')
        message: Optional completion message
    """
    with get_session() as session:
        job_run = session.query(JobRuns).filter_by(id=job_run_id).first()
        if job_run:
            job_run.ended_at = datetime.utcnow()
            job_run.status = status
            if message:
                job_run.message = message
            session.commit()


def log_job_failure(job_run_id: int, error_message: str):
    """
    Log a job failure.
    
    Args:
        job_run_id: ID of the job run that failed
        error_message: Error message describing the failure
    """
    log_job_completion(job_run_id, status='failed', message=error_message)

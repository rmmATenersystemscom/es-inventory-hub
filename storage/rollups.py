#!/usr/bin/env python3
"""
Data processing and rollup generation for es-inventory-hub
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

from common.config import config
from common.db import get_db_session
from common.logging import setup_logging, get_logger
from storage.models import (
    Site, Device, DeviceSnapshot, DailyCounts, MonthEndCounts
)

logger = get_logger(__name__)


class DataProcessor:
    """Handle data processing, rollups, and retention policies"""
    
    def __init__(self):
        self.snapshot_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    
    def generate_daily_rollups(self, db: Session, target_date: Optional[datetime] = None) -> Dict[str, int]:
        """
        Generate daily rollup counts from device snapshots
        
        Args:
            db: Database session
            target_date: Date to generate rollups for (defaults to today)
            
        Returns:
            Dict with processing statistics
        """
        if target_date is None:
            target_date = self.snapshot_date
        
        logger.info(f"Generating daily rollups for {target_date.date()}")
        
        try:
            # Get all sites
            sites = db.query(Site).all()
            stats = {
                'sites_processed': 0,
                'rollups_created': 0,
                'rollups_updated': 0,
                'errors': 0
            }
            
            for site in sites:
                try:
                    # Get device snapshots for this site and date
                    snapshots = db.query(DeviceSnapshot).join(Device).filter(
                        and_(
                            Device.site_id == site.id,
                            func.date(DeviceSnapshot.snapshot_date) == target_date.date()
                        )
                    ).all()
                    
                    if not snapshots:
                        logger.debug(f"No snapshots found for site {site.name} on {target_date.date()}")
                        continue
                    
                    # Calculate counts
                    counts = self._calculate_device_counts(snapshots)
                    
                    # Check if daily count already exists
                    existing_count = db.query(DailyCounts).filter(
                        and_(
                            DailyCounts.site_id == site.id,
                            func.date(DailyCounts.count_date) == target_date.date()
                        )
                    ).first()
                    
                    if existing_count:
                        # Update existing count
                        self._update_daily_count(existing_count, counts)
                        stats['rollups_updated'] += 1
                        logger.debug(f"Updated daily count for site {site.name}")
                    else:
                        # Create new count
                        daily_count = DailyCounts(
                            count_date=target_date,
                            site_id=site.id,
                            **counts
                        )
                        db.add(daily_count)
                        stats['rollups_created'] += 1
                        logger.debug(f"Created daily count for site {site.name}")
                    
                    stats['sites_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing site {site.name}: {e}")
                    stats['errors'] += 1
            
            db.commit()
            logger.info(f"Daily rollup generation completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to generate daily rollups: {e}")
            db.rollback()
            raise
    
    def generate_month_end_snapshots(self, db: Session, target_date: Optional[datetime] = None) -> Dict[str, int]:
        """
        Generate month-end snapshots for retention policy
        
        Args:
            db: Database session
            target_date: Date to check for month-end (defaults to today)
            
        Returns:
            Dict with processing statistics
        """
        if target_date is None:
            target_date = self.snapshot_date
        
        # Check if this is month-end (last day of month)
        next_month = target_date.replace(day=1) + timedelta(days=32)
        month_end = next_month.replace(day=1) - timedelta(days=1)
        
        if target_date.date() != month_end.date():
            logger.info(f"Not month-end ({target_date.date()}), skipping month-end snapshot generation")
            return {'month_end_snapshots_created': 0, 'month_end_snapshots_updated': 0}
        
        logger.info(f"Generating month-end snapshots for {target_date.date()}")
        
        try:
            # Get all sites
            sites = db.query(Site).all()
            stats = {
                'month_end_snapshots_created': 0,
                'month_end_snapshots_updated': 0,
                'errors': 0
            }
            
            for site in sites:
                try:
                    # Get device snapshots for this site and date
                    snapshots = db.query(DeviceSnapshot).join(Device).filter(
                        and_(
                            Device.site_id == site.id,
                            func.date(DeviceSnapshot.snapshot_date) == target_date.date()
                        )
                    ).all()
                    
                    if not snapshots:
                        logger.debug(f"No snapshots found for site {site.name} on {target_date.date()}")
                        continue
                    
                    # Calculate counts
                    counts = self._calculate_device_counts(snapshots)
                    
                    # Check if month-end count already exists
                    existing_count = db.query(MonthEndCounts).filter(
                        and_(
                            MonthEndCounts.site_id == site.id,
                            func.date(MonthEndCounts.month_end_date) == target_date.date()
                        )
                    ).first()
                    
                    if existing_count:
                        # Update existing count
                        self._update_month_end_count(existing_count, counts)
                        stats['month_end_snapshots_updated'] += 1
                        logger.debug(f"Updated month-end count for site {site.name}")
                    else:
                        # Create new count
                        month_end_count = MonthEndCounts(
                            month_end_date=target_date,
                            site_id=site.id,
                            **counts
                        )
                        db.add(month_end_count)
                        stats['month_end_snapshots_created'] += 1
                        logger.debug(f"Created month-end count for site {site.name}")
                    
                except Exception as e:
                    logger.error(f"Error processing month-end for site {site.name}: {e}")
                    stats['errors'] += 1
            
            db.commit()
            logger.info(f"Month-end snapshot generation completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to generate month-end snapshots: {e}")
            db.rollback()
            raise
    
    def enforce_retention_policy(self, db: Session) -> Dict[str, int]:
        """
        Enforce retention policy: keep 65 days of daily data + month-end snapshots
        
        Args:
            db: Database session
            
        Returns:
            Dict with cleanup statistics
        """
        logger.info("Enforcing retention policy")
        
        try:
            cutoff_date = self.snapshot_date - timedelta(days=65)
            stats = {
                'old_snapshots_deleted': 0,
                'old_daily_counts_deleted': 0,
                'month_end_counts_preserved': 0
            }
            
            # Delete old device snapshots (older than 65 days)
            old_snapshots = db.query(DeviceSnapshot).filter(
                DeviceSnapshot.snapshot_date < cutoff_date
            ).all()
            
            for snapshot in old_snapshots:
                db.delete(snapshot)
                stats['old_snapshots_deleted'] += 1
            
            # Delete old daily counts (older than 65 days)
            old_daily_counts = db.query(DailyCounts).filter(
                DailyCounts.count_date < cutoff_date
            ).all()
            
            for daily_count in old_daily_counts:
                db.delete(daily_count)
                stats['old_daily_counts_deleted'] += 1
            
            # Keep month-end counts (retain for 2 years)
            month_end_cutoff = self.snapshot_date - timedelta(days=730)  # 2 years
            old_month_end_counts = db.query(MonthEndCounts).filter(
                MonthEndCounts.month_end_date < month_end_cutoff
            ).all()
            
            for month_end_count in old_month_end_counts:
                db.delete(month_end_count)
                stats['month_end_counts_preserved'] += 1
            
            db.commit()
            logger.info(f"Retention policy enforcement completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to enforce retention policy: {e}")
            db.rollback()
            raise
    
    def _calculate_device_counts(self, snapshots: List[DeviceSnapshot]) -> Dict[str, int]:
        """Calculate device counts from snapshots"""
        counts = {
            'total_devices': len(snapshots),
            'servers': 0,
            'workstations': 0,
            'spare_devices': 0,
            'billable_devices': 0,
            'ninja_devices': 0,
            'threatlocker_devices': 0
        }
        
        for snapshot in snapshots:
            # Count by device type
            if snapshot.is_server:
                counts['servers'] += 1
            else:
                counts['workstations'] += 1
            
            # Count by spare status
            if snapshot.is_spare:
                counts['spare_devices'] += 1
            
            # Count by billable status
            if snapshot.is_billable:
                counts['billable_devices'] += 1
            
            # Count by source system
            if snapshot.source_system == 'ninja':
                counts['ninja_devices'] += 1
            elif snapshot.source_system == 'threatlocker':
                counts['threatlocker_devices'] += 1
        
        return counts
    
    def _update_daily_count(self, daily_count: DailyCounts, counts: Dict[str, int]) -> None:
        """Update existing daily count with new values"""
        daily_count.total_devices = counts['total_devices']
        daily_count.servers = counts['servers']
        daily_count.workstations = counts['workstations']
        daily_count.spare_devices = counts['spare_devices']
        daily_count.billable_devices = counts['billable_devices']
        daily_count.ninja_devices = counts['ninja_devices']
        daily_count.threatlocker_devices = counts['threatlocker_devices']
        daily_count.updated_at = datetime.now(timezone.utc)
    
    def _update_month_end_count(self, month_end_count: MonthEndCounts, counts: Dict[str, int]) -> None:
        """Update existing month-end count with new values"""
        month_end_count.total_devices = counts['total_devices']
        month_end_count.servers = counts['servers']
        month_end_count.workstations = counts['workstations']
        month_end_count.spare_devices = counts['spare_devices']
        month_end_count.billable_devices = counts['billable_devices']
        month_end_count.ninja_devices = counts['ninja_devices']
        month_end_count.threatlocker_devices = counts['threatlocker_devices']


def main():
    """Main entry point for data processing"""
    setup_logging()
    logger.info("Starting data processing pipeline")
    
    try:
        with get_db_session() as db:
            processor = DataProcessor()
            
            # Generate daily rollups
            daily_stats = processor.generate_daily_rollups(db)
            logger.info(f"Daily rollups: {daily_stats}")
            
            # Generate month-end snapshots (if applicable)
            month_end_stats = processor.generate_month_end_snapshots(db)
            logger.info(f"Month-end snapshots: {month_end_stats}")
            
            # Enforce retention policy
            retention_stats = processor.enforce_retention_policy(db)
            logger.info(f"Retention policy: {retention_stats}")
            
        logger.info("Data processing pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Data processing pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

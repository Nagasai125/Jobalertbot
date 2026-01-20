"""
Scheduler for periodic job monitoring.
Uses APScheduler for configurable interval-based polling.
"""

import logging
import signal
import sys
from typing import Callable, Optional

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class JobScheduler:
    """Scheduler for periodic job monitoring tasks."""
    
    def __init__(self, interval_minutes: int = 10, daily_summary_hour: int = None):
        """
        Initialize the scheduler.
        
        Args:
            interval_minutes: Minutes between job checks.
            daily_summary_hour: Hour (UTC) to send daily summary, None to disable.
        """
        self.interval_minutes = interval_minutes
        self.daily_summary_hour = daily_summary_hour
        self.scheduler: Optional[BlockingScheduler] = None
        self._job_func: Optional[Callable] = None
        self._summary_func: Optional[Callable] = None
    
    def start(self, job_func: Callable, summary_func: Callable = None):
        """
        Start the scheduler with the given job function.
        
        Args:
            job_func: Function to call on each interval.
            summary_func: Function to call for daily summary.
        """
        self._job_func = job_func
        self._summary_func = summary_func
        self.scheduler = BlockingScheduler()
        
        # Add the job with interval trigger
        self.scheduler.add_job(
            job_func,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id='job_monitor',
            name='Job Monitor',
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )
        
        # Add daily summary job if configured
        if self.daily_summary_hour is not None and summary_func:
            self.scheduler.add_job(
                summary_func,
                trigger=CronTrigger(hour=self.daily_summary_hour, minute=0),
                id='daily_summary',
                name='Daily Summary',
                replace_existing=True
            )
            logger.info(f"Daily summary scheduled at {self.daily_summary_hour}:00 UTC")
        
        # Set up graceful shutdown
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)
        
        logger.info(f"Scheduler started. Checking every {self.interval_minutes} minutes.")
        
        # Run immediately on start, then schedule
        try:
            logger.info("Running initial job check...")
            job_func()
        except Exception as e:
            logger.error(f"Initial job check failed: {e}")
        
        # Start the scheduler (blocking)
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            self._shutdown()
    
    def _shutdown(self, signum=None, frame=None):
        """Gracefully shutdown the scheduler."""
        logger.info("Shutting down scheduler...")
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
        sys.exit(0)
    
    def run_once(self, job_func: Callable):
        """
        Run the job function once without scheduling.
        Useful for testing.
        
        Args:
            job_func: Function to call.
        """
        logger.info("Running single job check...")
        job_func()
        logger.info("Single job check complete.")

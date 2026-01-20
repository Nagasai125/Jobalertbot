"""
Base notifier interface for job alerts system.
All notification channels inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List
import logging

from ..database import Job

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """Abstract base class for notification channels."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this notification channel."""
        pass
    
    @abstractmethod
    def send(self, job: Job) -> bool:
        """
        Send a notification for a single job.
        
        Args:
            job: The Job to notify about.
            
        Returns:
            True if notification was sent successfully, False otherwise.
        """
        pass
    
    def send_batch(self, jobs: List[Job]) -> int:
        """
        Send notifications for multiple jobs.
        
        Args:
            jobs: List of Jobs to notify about.
            
        Returns:
            Number of successfully sent notifications.
        """
        success_count = 0
        for job in jobs:
            try:
                if self.send(job):
                    success_count += 1
            except Exception as e:
                logger.error(f"Failed to send notification for {job.title}: {e}")
        
        logger.info(f"{self.name}: Sent {success_count}/{len(jobs)} notifications")
        return success_count
    
    def format_job_message(self, job: Job) -> str:
        """
        Format a job as a human-readable message.
        
        Args:
            job: The Job to format.
            
        Returns:
            Formatted message string.
        """
        parts = [
            f"🚀 *New Job Alert!*",
            f"",
            f"*{job.title}*",
            f"🏢 {job.company}",
        ]
        
        if job.location:
            parts.append(f"📍 {job.location}")
        
        if job.job_type:
            parts.append(f"💼 {job.job_type}")
        
        parts.extend([
            f"",
            f"🔗 {job.url}"
        ])
        
        return "\n".join(parts)

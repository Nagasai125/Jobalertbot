"""
Database layer for Job Alerts system.
Handles job storage, deduplication, and notification tracking.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class Job:
    """Represents a job posting."""
    id: Optional[int] = None
    company: str = ""
    title: str = ""
    url: str = ""
    location: str = ""
    job_type: str = ""
    description: str = ""
    first_seen: Optional[datetime] = None
    notified: bool = False
    
    def __hash__(self):
        return hash(self.url)
    
    def __eq__(self, other):
        if isinstance(other, Job):
            return self.url == other.url
        return False


class JobDatabase:
    """SQLite database for job storage and deduplication."""
    
    def __init__(self, db_path: str = "data/jobs.db"):
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                location TEXT,
                job_type TEXT,
                description TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified BOOLEAN DEFAULT 0
            )
        ''')
        
        # Index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_jobs_url ON jobs(url)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_jobs_notified ON jobs(notified)
        ''')
        
        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    def job_exists(self, url: str) -> bool:
        """
        Check if a job already exists in the database.
        
        Args:
            url: The job posting URL.
            
        Returns:
            True if job exists, False otherwise.
        """
        cursor = self.conn.cursor()
        cursor.execute('SELECT 1 FROM jobs WHERE url = ?', (url,))
        return cursor.fetchone() is not None
    
    def add_job(self, job: Job) -> bool:
        """
        Add a new job to the database.
        
        Args:
            job: The Job object to add.
            
        Returns:
            True if job was added, False if it already exists.
        """
        if self.job_exists(job.url):
            logger.debug(f"Job already exists: {job.url}")
            return False
        
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO jobs (company, title, url, location, job_type, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (job.company, job.title, job.url, job.location, job.job_type, job.description))
            self.conn.commit()
            job.id = cursor.lastrowid
            logger.info(f"Added new job: {job.title} at {job.company}")
            return True
        except sqlite3.IntegrityError:
            logger.debug(f"Job already exists (race condition): {job.url}")
            return False
    
    def mark_notified(self, job: Job) -> None:
        """
        Mark a job as notified.
        
        Args:
            job: The Job object to mark.
        """
        cursor = self.conn.cursor()
        cursor.execute('UPDATE jobs SET notified = 1 WHERE url = ?', (job.url,))
        self.conn.commit()
        logger.debug(f"Marked job as notified: {job.url}")
    
    def get_unnotified_jobs(self) -> List[Job]:
        """
        Get all jobs that haven't been notified yet.
        
        Returns:
            List of Job objects that need notification.
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, company, title, url, location, job_type, description, first_seen, notified
            FROM jobs WHERE notified = 0
        ''')
        
        jobs = []
        for row in cursor.fetchall():
            jobs.append(Job(
                id=row['id'],
                company=row['company'],
                title=row['title'],
                url=row['url'],
                location=row['location'],
                job_type=row['job_type'],
                description=row['description'],
                first_seen=datetime.fromisoformat(row['first_seen']) if row['first_seen'] else None,
                notified=bool(row['notified'])
            ))
        
        return jobs
    
    def get_job_count(self) -> int:
        """Get total number of jobs in database."""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM jobs')
        return cursor.fetchone()[0]
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

"""
Email notification channel.
Sends job alerts via SMTP email.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from .base import BaseNotifier
from ..database import Job
from ..config import EmailConfig

logger = logging.getLogger(__name__)


class EmailNotifier(BaseNotifier):
    """Send job notifications via email."""
    
    def __init__(self, config: EmailConfig):
        """
        Initialize email notifier.
        
        Args:
            config: Email configuration with SMTP settings.
        """
        self.config = config
    
    @property
    def name(self) -> str:
        return "Email"
    
    def send(self, job: Job) -> bool:
        """
        Send a job notification via email.
        
        Args:
            job: The Job to notify about.
            
        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.config.enabled:
            logger.debug("Email notifications disabled")
            return False
        
        if not all([self.config.sender_email, self.config.sender_password, 
                    self.config.recipient_email]):
            logger.error("Email configuration incomplete")
            return False
        
        subject = f"🚀 New Job: {job.title} at {job.company}"
        html_body = self._format_html_email(job)
        text_body = self._format_text_email(job)
        
        return self._send_email(subject, html_body, text_body)
    
    def send_batch(self, jobs: List[Job]) -> int:
        """
        Send a digest email for multiple jobs.
        
        Args:
            jobs: List of Jobs to notify about.
            
        Returns:
            Number of jobs included (1 if sent, 0 if failed).
        """
        if not self.config.enabled or not jobs:
            return 0
        
        # For batch, send a digest email
        subject = f"🚀 {len(jobs)} New Job Alerts"
        html_body = self._format_digest_html(jobs)
        text_body = self._format_digest_text(jobs)
        
        if self._send_email(subject, html_body, text_body):
            return len(jobs)
        return 0
    
    def _send_email(self, subject: str, html_body: str, text_body: str) -> bool:
        """Send an email via SMTP."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config.sender_email
            msg['To'] = self.config.recipient_email
            
            # Attach both plain text and HTML versions
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Connect and send
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.sender_email, self.config.sender_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {self.config.recipient_email}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Email authentication failed. Check your credentials.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _format_html_email(self, job: Job) -> str:
        """Format a single job as HTML email."""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h1 style="color: #2c3e50; margin-bottom: 20px;">🚀 New Job Alert!</h1>
                
                <div style="background: #ecf0f1; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                    <h2 style="color: #34495e; margin: 0 0 10px 0;">{job.title}</h2>
                    <p style="margin: 5px 0; color: #7f8c8d;">
                        🏢 <strong>{job.company}</strong>
                    </p>
                    {f'<p style="margin: 5px 0; color: #7f8c8d;">📍 {job.location}</p>' if job.location else ''}
                    {f'<p style="margin: 5px 0; color: #7f8c8d;">💼 {job.job_type}</p>' if job.job_type else ''}
                </div>
                
                <a href="{job.url}" style="display: inline-block; background: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Apply Now →
                </a>
                
                <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">
                <p style="color: #95a5a6; font-size: 12px;">
                    This alert was sent by Job Alert System
                </p>
            </div>
        </body>
        </html>
        """
    
    def _format_text_email(self, job: Job) -> str:
        """Format a single job as plain text email."""
        parts = [
            "🚀 NEW JOB ALERT!",
            "=" * 40,
            "",
            f"Title: {job.title}",
            f"Company: {job.company}",
        ]
        
        if job.location:
            parts.append(f"Location: {job.location}")
        if job.job_type:
            parts.append(f"Type: {job.job_type}")
        
        parts.extend([
            "",
            f"Apply: {job.url}",
            "",
            "-" * 40,
            "Sent by Job Alert System"
        ])
        
        return "\n".join(parts)
    
    def _format_digest_html(self, jobs: List[Job]) -> str:
        """Format multiple jobs as HTML digest email."""
        job_cards = ""
        for job in jobs:
            job_cards += f"""
            <div style="background: #ecf0f1; border-radius: 8px; padding: 15px; margin-bottom: 15px;">
                <h3 style="color: #34495e; margin: 0 0 8px 0;">
                    <a href="{job.url}" style="color: #3498db; text-decoration: none;">{job.title}</a>
                </h3>
                <p style="margin: 3px 0; color: #7f8c8d; font-size: 14px;">
                    🏢 {job.company}
                    {f' • 📍 {job.location}' if job.location else ''}
                </p>
            </div>
            """
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h1 style="color: #2c3e50; margin-bottom: 20px;">🚀 {len(jobs)} New Job Alerts!</h1>
                
                {job_cards}
                
                <hr style="border: none; border-top: 1px solid #ecf0f1; margin: 20px 0;">
                <p style="color: #95a5a6; font-size: 12px;">
                    This digest was sent by Job Alert System
                </p>
            </div>
        </body>
        </html>
        """
    
    def _format_digest_text(self, jobs: List[Job]) -> str:
        """Format multiple jobs as plain text digest."""
        parts = [
            f"🚀 {len(jobs)} NEW JOB ALERTS!",
            "=" * 40,
            ""
        ]
        
        for i, job in enumerate(jobs, 1):
            parts.extend([
                f"{i}. {job.title}",
                f"   Company: {job.company}",
            ])
            if job.location:
                parts.append(f"   Location: {job.location}")
            parts.append(f"   Apply: {job.url}")
            parts.append("")
        
        parts.extend([
            "-" * 40,
            "Sent by Job Alert System"
        ])
        
        return "\n".join(parts)

"""
Telegram notification channel.
Sends job alerts via Telegram bot.
Implementation updated to use synchronous requests to avoid event loops issues.
"""

import logging
import requests
from time import sleep

from .base import BaseNotifier
from ..database import Job
from ..config import TelegramConfig

logger = logging.getLogger(__name__)


class TelegramNotifier(BaseNotifier):
    """Send job notifications via Telegram bot."""
    
    def __init__(self, config: TelegramConfig):
        """
        Initialize Telegram notifier.
        
        Args:
            config: Telegram configuration with bot_token and chat_id.
        """
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
        
        if not config.bot_token:
            logger.warning("Telegram bot token missing")
    
    @property
    def name(self) -> str:
        return "Telegram"
    
    def send(self, job: Job) -> bool:
        """
        Send a job notification via Telegram.
        
        Args:
            job: The Job to notify about.
            
        Returns:
            True if sent successfully, False otherwise.
        """
        if not self.config.enabled:
            return False
        
        if not self.config.chat_id:
            logger.error("Telegram chat_id not configured")
            return False
        
        message = self._format_telegram_message(job)
        
        payload = {
            'chat_id': self.config.chat_id,
            'text': message,
            'parse_mode': 'MarkdownV2',
            'disable_web_page_preview': False
        }
        
        try:
            response = requests.post(self.base_url, json=payload, timeout=10)
            
            if response.status_code == 429:
                # Rate limited
                retry_after = response.json().get('parameters', {}).get('retry_after', 5)
                logger.warning(f"Telegram rate limit, waiting {retry_after}s")
                sleep(retry_after)
                return self.send(job)  # Retry once
                
            response.raise_for_status()
            logger.info(f"Telegram notification sent for: {job.title}")
            return True
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Telegram HTTP error: {e.response.text if e.response else e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    def _format_telegram_message(self, job: Job) -> str:
        """
        Format job as Telegram message with MarkdownV2.
        """
        title = self._escape_markdown(job.title)
        company = self._escape_markdown(job.company)
        location = self._escape_markdown(job.location) if job.location else ""
        job_type = self._escape_markdown(job.job_type) if job.job_type else ""
        
        parts = [
            "🚀 *New Job Alert\\!*",
            "",
            f"*{title}*",
            f"🏢 {company}",
        ]
        
        if location:
            parts.append(f"📍 {location}")
        
        if job_type:
            parts.append(f"💼 {job_type}")
        
        parts.extend([
            "",
            f"🔗 [Apply Here]({job.url})"
        ])
        
        return "\n".join(parts)
    
    def _escape_markdown(self, text: str) -> str:
        """Escape special characters for Telegram MarkdownV2."""
        if not text:
            return ""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

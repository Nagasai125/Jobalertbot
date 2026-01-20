"""
Telegram notification channel.
Sends job alerts via Telegram bot.
"""

import logging
import asyncio
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

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
        self.bot: Optional[Bot] = None
        
        if config.enabled and config.bot_token:
            self.bot = Bot(token=config.bot_token)
    
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
        if not self.config.enabled or not self.bot:
            logger.debug("Telegram notifications disabled")
            return False
        
        if not self.config.chat_id:
            logger.error("Telegram chat_id not configured")
            return False
        
        message = self._format_telegram_message(job)
        
        try:
            # Run async send in sync context
            asyncio.run(self._send_message(message))
            logger.info(f"Telegram notification sent for: {job.title}")
            return True
        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
    
    async def _send_message(self, message: str):
        """Send message asynchronously."""
        await self.bot.send_message(
            chat_id=self.config.chat_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False
        )
    
    def _format_telegram_message(self, job: Job) -> str:
        """
        Format job as Telegram message with Markdown.
        
        Args:
            job: The Job to format.
            
        Returns:
            Formatted Telegram message.
        """
        # Escape special Markdown characters in dynamic content
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

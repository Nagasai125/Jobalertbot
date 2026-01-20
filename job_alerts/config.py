"""
Configuration management for Job Alerts system.
Loads YAML config and provides typed access to settings.
"""

import os
import re
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class CompanyConfig:
    """Configuration for a target company."""
    name: str
    url: str
    scraper: str


@dataclass
class KeywordsConfig:
    """Keyword matching configuration."""
    include: List[str] = field(default_factory=list)
    exclude: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)


@dataclass
class MatchingConfig:
    """Matching algorithm configuration."""
    mode: str = "tokenized"  # exact | tokenized | fuzzy
    fuzzy_threshold: float = 0.85
    case_sensitive: bool = False


@dataclass
class TelegramConfig:
    """Telegram notification configuration."""
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


@dataclass
class EmailConfig:
    """Email notification configuration."""
    enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""
    recipient_email: str = ""


@dataclass
class NotificationsConfig:
    """All notification channels configuration."""
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    email: EmailConfig = field(default_factory=EmailConfig)


@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "data/jobs.db"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: str = "logs/job_alerts.log"


@dataclass
class PollingConfig:
    """Polling configuration."""
    interval_minutes: int = 10


@dataclass
class Config:
    """Main configuration object."""
    polling: PollingConfig = field(default_factory=PollingConfig)
    companies: List[CompanyConfig] = field(default_factory=list)
    keywords: KeywordsConfig = field(default_factory=KeywordsConfig)
    matching: MatchingConfig = field(default_factory=MatchingConfig)
    notifications: NotificationsConfig = field(default_factory=NotificationsConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


def _expand_env_vars(value: str) -> str:
    """Expand environment variables in format ${VAR_NAME}."""
    if not isinstance(value, str):
        return value
    
    pattern = re.compile(r'\$\{([^}]+)\}')
    
    def replace(match):
        env_var = match.group(1)
        return os.environ.get(env_var, match.group(0))
    
    return pattern.sub(replace, value)


def _expand_env_vars_recursive(obj):
    """Recursively expand environment variables in a dict/list structure."""
    if isinstance(obj, dict):
        return {k: _expand_env_vars_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_env_vars_recursive(item) for item in obj]
    elif isinstance(obj, str):
        return _expand_env_vars(obj)
    return obj


def load_config(config_path: str = "config/config.yaml") -> Config:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to the YAML configuration file.
        
    Returns:
        Config object with all settings.
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(path, 'r') as f:
        raw_config = yaml.safe_load(f)
    
    # Expand environment variables
    raw_config = _expand_env_vars_recursive(raw_config)
    
    # Build config object
    config = Config()
    
    # Polling
    if 'polling' in raw_config:
        config.polling = PollingConfig(
            interval_minutes=raw_config['polling'].get('interval_minutes', 10)
        )
    
    # Companies
    if 'companies' in raw_config:
        config.companies = [
            CompanyConfig(
                name=c['name'],
                url=c['url'],
                scraper=c.get('scraper', 'generic')
            )
            for c in raw_config['companies']
        ]
    
    # Keywords
    if 'keywords' in raw_config:
        kw = raw_config['keywords']
        config.keywords = KeywordsConfig(
            include=kw.get('include', []),
            exclude=kw.get('exclude', []),
            locations=kw.get('locations', [])
        )
    
    # Matching
    if 'matching' in raw_config:
        m = raw_config['matching']
        config.matching = MatchingConfig(
            mode=m.get('mode', 'tokenized'),
            fuzzy_threshold=m.get('fuzzy_threshold', 0.85),
            case_sensitive=m.get('case_sensitive', False)
        )
    
    # Notifications
    if 'notifications' in raw_config:
        notif = raw_config['notifications']
        
        telegram_config = TelegramConfig()
        if 'telegram' in notif:
            tg = notif['telegram']
            telegram_config = TelegramConfig(
                enabled=tg.get('enabled', False),
                bot_token=tg.get('bot_token', ''),
                chat_id=tg.get('chat_id', '')
            )
        
        email_config = EmailConfig()
        if 'email' in notif:
            em = notif['email']
            email_config = EmailConfig(
                enabled=em.get('enabled', False),
                smtp_host=em.get('smtp_host', 'smtp.gmail.com'),
                smtp_port=em.get('smtp_port', 587),
                sender_email=em.get('sender_email', ''),
                sender_password=em.get('sender_password', ''),
                recipient_email=em.get('recipient_email', '')
            )
        
        config.notifications = NotificationsConfig(
            telegram=telegram_config,
            email=email_config
        )
    
    # Database
    if 'database' in raw_config:
        config.database = DatabaseConfig(
            path=raw_config['database'].get('path', 'data/jobs.db')
        )
    
    # Logging
    if 'logging' in raw_config:
        config.logging = LoggingConfig(
            level=raw_config['logging'].get('level', 'INFO'),
            file=raw_config['logging'].get('file', 'logs/job_alerts.log')
        )
    
    return config

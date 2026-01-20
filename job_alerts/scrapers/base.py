"""
Base scraper interface for job alerts system.
All company-specific scrapers inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import logging
import time
import random

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..database import Job

logger = logging.getLogger(__name__)


# Common user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class BaseScraper(ABC):
    """Abstract base class for job scrapers."""
    
    def __init__(self, company_name: str, base_url: str):
        """
        Initialize the scraper.
        
        Args:
            company_name: Name of the company.
            base_url: Base URL for the company's career page.
        """
        self.company_name = company_name
        self.base_url = base_url
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retries and headers."""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        
        return session
    
    def _rate_limit(self, min_delay: float = 1.0, max_delay: float = 3.0):
        """Add random delay between requests to avoid rate limiting."""
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
    
    def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a page and return its HTML content.
        
        Args:
            url: URL to fetch.
            
        Returns:
            HTML content as string, or None on error.
        """
        try:
            self._rate_limit()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    @abstractmethod
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from the company's career page.
        
        Returns:
            List of Job objects found.
        """
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(company={self.company_name})"

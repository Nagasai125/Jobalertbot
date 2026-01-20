"""
GitHub careers page scraper.
"""

from typing import List
import logging
import re

from bs4 import BeautifulSoup

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class GitHubScraper(BaseScraper):
    """Scraper for GitHub's careers page."""
    
    def __init__(self, base_url: str = "https://github.com/about/careers"):
        super().__init__(company_name="GitHub", base_url=base_url)
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from GitHub's careers page.
        
        Note: GitHub's careers page structure may change. This scraper
        attempts to extract job listings from the main careers page.
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        
        html = self._fetch_page(self.base_url)
        if not html:
            logger.warning(f"Failed to fetch GitHub careers page")
            return jobs
        
        soup = BeautifulSoup(html, 'lxml')
        
        # GitHub's job listings are typically in a structured format
        # Try multiple selectors as page structure may vary
        job_elements = (
            soup.select('a[href*="/about/careers/"]') or
            soup.select('.job-listing') or
            soup.select('[data-job]') or
            soup.find_all('a', href=re.compile(r'/jobs?/|/careers?/|/positions?/'))
        )
        
        seen_urls = set()
        
        for element in job_elements:
            try:
                # Extract job URL
                if element.name == 'a':
                    href = element.get('href', '')
                else:
                    link = element.find('a')
                    href = link.get('href', '') if link else ''
                
                if not href or href in seen_urls:
                    continue
                
                # Make absolute URL
                if href.startswith('/'):
                    url = f"https://github.com{href}"
                elif not href.startswith('http'):
                    continue
                else:
                    url = href
                
                # Skip non-job links
                if '/careers' not in url or url == self.base_url:
                    continue
                
                seen_urls.add(url)
                
                # Extract title
                title = element.get_text(strip=True)
                if not title or len(title) > 200:
                    continue
                
                # Extract location if available
                location = ""
                parent = element.parent
                if parent:
                    location_elem = parent.find(class_=re.compile(r'location|place|city'))
                    if location_elem:
                        location = location_elem.get_text(strip=True)
                
                job = Job(
                    company=self.company_name,
                    title=title,
                    url=url,
                    location=location,
                    job_type="Full-time",
                    description=""
                )
                jobs.append(job)
                logger.debug(f"Found GitHub job: {title}")
                
            except Exception as e:
                logger.error(f"Error parsing GitHub job element: {e}")
                continue
        
        logger.info(f"Scraped {len(jobs)} jobs from GitHub")
        return jobs

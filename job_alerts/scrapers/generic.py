"""
Generic scraper that can be configured via CSS selectors.
Allows adding new companies without code changes.
"""

from typing import List, Optional
import logging
import re

from bs4 import BeautifulSoup

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class GenericScraper(BaseScraper):
    """
    Generic configurable scraper using CSS selectors.
    
    This scraper can be configured to work with most career pages
    by specifying the CSS selectors for job elements.
    """
    
    def __init__(
        self,
        company_name: str,
        base_url: str,
        job_selector: str = "a[href*=job], a[href*=career], a[href*=position]",
        title_selector: Optional[str] = None,
        location_selector: Optional[str] = None,
        url_attribute: str = "href"
    ):
        """
        Initialize the generic scraper.
        
        Args:
            company_name: Name of the company.
            base_url: URL to scrape.
            job_selector: CSS selector for job listing elements.
            title_selector: CSS selector for job title (relative to job element).
            location_selector: CSS selector for location (relative to job element).
            url_attribute: Attribute containing the job URL.
        """
        super().__init__(company_name=company_name, base_url=base_url)
        self.job_selector = job_selector
        self.title_selector = title_selector
        self.location_selector = location_selector
        self.url_attribute = url_attribute
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings using configured selectors.
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        
        html = self._fetch_page(self.base_url)
        if not html:
            logger.warning(f"Failed to fetch {self.company_name} careers page")
            return jobs
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Find job elements
        job_elements = soup.select(self.job_selector)
        
        seen_urls = set()
        base_domain = re.match(r'(https?://[^/]+)', self.base_url)
        base_domain = base_domain.group(1) if base_domain else ""
        
        for element in job_elements:
            try:
                # Extract URL
                if element.name == 'a':
                    href = element.get(self.url_attribute, '')
                else:
                    link = element.find('a')
                    href = link.get(self.url_attribute, '') if link else ''
                
                if not href or href in seen_urls:
                    continue
                
                # Make absolute URL
                if href.startswith('/'):
                    url = f"{base_domain}{href}"
                elif not href.startswith('http'):
                    continue
                else:
                    url = href
                
                seen_urls.add(url)
                
                # Extract title
                if self.title_selector:
                    title_elem = element.select_one(self.title_selector)
                    title = title_elem.get_text(strip=True) if title_elem else ""
                else:
                    title = element.get_text(strip=True)
                
                if not title or len(title) > 200:
                    continue
                
                # Extract location
                location = ""
                if self.location_selector:
                    loc_elem = element.select_one(self.location_selector)
                    if loc_elem:
                        location = loc_elem.get_text(strip=True)
                
                job = Job(
                    company=self.company_name,
                    title=title,
                    url=url,
                    location=location,
                    job_type="Full-time",
                    description=""
                )
                jobs.append(job)
                logger.debug(f"Found {self.company_name} job: {title}")
                
            except Exception as e:
                logger.error(f"Error parsing {self.company_name} job element: {e}")
                continue
        
        logger.info(f"Scraped {len(jobs)} jobs from {self.company_name}")
        return jobs

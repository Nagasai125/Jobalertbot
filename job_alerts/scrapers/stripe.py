"""
Stripe careers page scraper.
"""

from typing import List
import logging
import json
import re

from bs4 import BeautifulSoup

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class StripeScraper(BaseScraper):
    """Scraper for Stripe's careers page."""
    
    def __init__(self, base_url: str = "https://stripe.com/jobs/search"):
        super().__init__(company_name="Stripe", base_url=base_url)
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from Stripe's careers page.
        
        Stripe often uses a JavaScript-heavy page, so we try to:
        1. Look for job data in embedded JSON
        2. Parse the HTML for job links
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        
        html = self._fetch_page(self.base_url)
        if not html:
            logger.warning(f"Failed to fetch Stripe careers page")
            return jobs
        
        # Try to find embedded JSON data
        jobs_from_json = self._parse_json_data(html)
        if jobs_from_json:
            return jobs_from_json
        
        # Fallback to HTML parsing
        return self._parse_html(html)
    
    def _parse_json_data(self, html: str) -> List[Job]:
        """Try to extract job data from embedded JSON."""
        jobs = []
        
        # Look for JSON-LD or embedded job data
        soup = BeautifulSoup(html, 'lxml')
        
        # Check for JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'JobPosting':
                            job = self._parse_job_posting(item)
                            if job:
                                jobs.append(job)
                elif data.get('@type') == 'JobPosting':
                    job = self._parse_job_posting(data)
                    if job:
                        jobs.append(job)
            except (json.JSONDecodeError, TypeError):
                continue
        
        # Check for embedded job data in scripts
        for script in soup.find_all('script'):
            if script.string and 'jobs' in script.string.lower():
                # Try to extract JSON objects
                matches = re.findall(r'\{[^{}]*"title"[^{}]*"url"[^{}]*\}', script.string)
                for match in matches:
                    try:
                        data = json.loads(match)
                        job = Job(
                            company=self.company_name,
                            title=data.get('title', ''),
                            url=data.get('url', ''),
                            location=data.get('location', ''),
                            job_type=data.get('type', 'Full-time'),
                            description=data.get('description', '')[:500] if data.get('description') else ''
                        )
                        if job.title and job.url:
                            jobs.append(job)
                    except (json.JSONDecodeError, TypeError):
                        continue
        
        if jobs:
            logger.info(f"Extracted {len(jobs)} jobs from Stripe JSON data")
        
        return jobs
    
    def _parse_job_posting(self, data: dict) -> Job:
        """Parse a JobPosting JSON-LD object."""
        try:
            location = ""
            if 'jobLocation' in data:
                loc = data['jobLocation']
                if isinstance(loc, dict):
                    address = loc.get('address', {})
                    if isinstance(address, dict):
                        location = address.get('addressLocality', '')
                elif isinstance(loc, list) and loc:
                    address = loc[0].get('address', {})
                    location = address.get('addressLocality', '') if isinstance(address, dict) else ''
            
            return Job(
                company=self.company_name,
                title=data.get('title', ''),
                url=data.get('url', ''),
                location=location,
                job_type=data.get('employmentType', 'Full-time'),
                description=data.get('description', '')[:500] if data.get('description') else ''
            )
        except Exception as e:
            logger.error(f"Error parsing JobPosting: {e}")
            return None
    
    def _parse_html(self, html: str) -> List[Job]:
        """Fallback HTML parsing for job listings."""
        jobs = []
        soup = BeautifulSoup(html, 'lxml')
        
        seen_urls = set()
        
        # Try to find job links
        job_links = soup.find_all('a', href=re.compile(r'/jobs/|/careers/|/positions?/'))
        
        for link in job_links:
            try:
                href = link.get('href', '')
                if not href or href in seen_urls:
                    continue
                
                # Make absolute URL
                if href.startswith('/'):
                    url = f"https://stripe.com{href}"
                elif not href.startswith('http'):
                    continue
                else:
                    url = href
                
                # Skip search page and non-job pages
                if '/jobs/search' in url or url == self.base_url:
                    continue
                
                seen_urls.add(url)
                
                title = link.get_text(strip=True)
                if not title or len(title) > 200:
                    continue
                
                # Try to find location
                location = ""
                parent = link.parent
                if parent:
                    location_elem = parent.find(class_=re.compile(r'location|place|city|region'))
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
                logger.debug(f"Found Stripe job: {title}")
                
            except Exception as e:
                logger.error(f"Error parsing Stripe job link: {e}")
                continue
        
        logger.info(f"Scraped {len(jobs)} jobs from Stripe HTML")
        return jobs

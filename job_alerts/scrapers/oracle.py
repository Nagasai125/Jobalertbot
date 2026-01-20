"""
Oracle Cloud HCM scraper for companies using Oracle recruiting.
Ford and other companies use Oracle Cloud for their job listings.
"""

from typing import List
import logging
import json

import requests
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class OracleScraper(BaseScraper):
    """Scraper for companies using Oracle Cloud HCM recruiting."""
    
    def __init__(self, company_name: str = "Ford", base_url: str = "https://careers.ford.com"):
        """
        Initialize Oracle HCM scraper.
        
        Args:
            company_name: Name of the company
            base_url: Company careers page URL
        """
        super().__init__(company_name=company_name, base_url=base_url)
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from Oracle Cloud HCM.
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        
        # Ford uses a custom careers site, try direct scraping
        try:
            search_url = f"{self.base_url}/job-search-results/"
            
            self._rate_limit(0.5, 1.5)
            response = self.session.get(
                search_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml"
                },
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Look for job listing links
            job_links = soup.select('a[href*="job"], a[href*="position"], a[href*="careers"]')
            
            seen_urls = set()
            for link in job_links:
                href = link.get('href', '')
                
                # Skip if not a job link
                if not href or href in seen_urls:
                    continue
                if 'job-search' in href.lower() and 'results' not in href.lower():
                    continue
                
                title = link.get_text(strip=True)
                if not title or len(title) > 200 or len(title) < 5:
                    continue
                
                # Skip navigation links
                if title.lower() in ['jobs', 'careers', 'search', 'home', 'apply', 'back']:
                    continue
                
                # Make absolute URL
                if href.startswith('/'):
                    href = f"{self.base_url}{href}"
                elif not href.startswith('http'):
                    continue
                
                seen_urls.add(href)
                
                # Try to find location
                parent = link.find_parent(['div', 'li', 'article'])
                location = ""
                if parent:
                    loc_elem = parent.select_one('[class*="location"], [data-location]')
                    if loc_elem:
                        location = loc_elem.get_text(strip=True)
                
                job = Job(
                    company=self.company_name,
                    title=title,
                    url=href,
                    location=location or "USA",
                    job_type="Full-time",
                    description=""
                )
                jobs.append(job)
            
            # If we didn't find jobs, try the Oracle API endpoint
            if not jobs:
                jobs = self._scrape_oracle_api()
            
        except requests.RequestException as e:
            logger.error(f"{self.company_name} scrape error: {e}")
            jobs = self._scrape_oracle_api()
        
        logger.info(f"Scraped {len(jobs)} jobs from {self.company_name}")
        return jobs
    
    def _scrape_oracle_api(self) -> List[Job]:
        """Try Oracle Cloud HCM REST API."""
        jobs = []
        
        try:
            # Common Oracle HCM API patterns
            api_endpoints = [
                "https://efds.fa.em5.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions",
                f"{self.base_url}/api/jobs",
            ]
            
            for api_url in api_endpoints:
                try:
                    response = self.session.get(
                        api_url,
                        params={"limit": 100, "onlyData": "true"},
                        headers={
                            "Accept": "application/json",
                            "User-Agent": "Mozilla/5.0"
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        items = data.get("items", data.get("jobs", []))
                        
                        for item in items:
                            job = Job(
                                company=self.company_name,
                                title=item.get("Title", item.get("title", "")),
                                url=item.get("JobUrl", item.get("url", f"{self.base_url}/job/{item.get('Id', '')}")),
                                location=item.get("PrimaryLocation", item.get("location", "USA")),
                                job_type="Full-time",
                                description=""
                            )
                            if job.title:
                                jobs.append(job)
                        
                        if jobs:
                            break
                            
                except Exception:
                    continue
                    
        except Exception as e:
            logger.error(f"{self.company_name} Oracle API error: {e}")
        
        return jobs

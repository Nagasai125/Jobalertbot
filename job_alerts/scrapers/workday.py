"""
Workday-based company scraper.
Many companies use Workday for their job listings (LiveRamp, etc.).
"""

from typing import List
import logging
import json
import re

import requests

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class WorkdayScraper(BaseScraper):
    """Scraper for companies using Workday job portals."""
    
    def __init__(self, company_name: str, base_url: str):
        """
        Initialize Workday scraper.
        
        Args:
            company_name: Name of the company
            base_url: Workday URL (can be human-readable or API endpoint)
                     e.g., https://liveramp.wd5.myworkdayjobs.com/LiveRampCareers
                     or https://company.wd5.myworkdayjobs.com/wday/cxs/company/site/jobs
        """
        super().__init__(company_name=company_name, base_url=base_url)
        self.api_url = self._construct_api_url(base_url)
        self.site_url = self._get_site_url(base_url)
    
    def _construct_api_url(self, url: str) -> str:
        """Convert human-readable Workday URL to API endpoint."""
        # If already an API URL, return as-is
        if "/wday/cxs/" in url:
            return url
        
        # Parse: https://company.wd5.myworkdayjobs.com/SiteName
        match = re.match(r'https?://([^.]+)\.(wd\d+)\.myworkdayjobs\.com/([^/?]+)', url)
        if match:
            company = match.group(1)
            wd_instance = match.group(2)
            site_name = match.group(3)
            return f"https://{company}.{wd_instance}.myworkdayjobs.com/wday/cxs/{company}/{site_name}/jobs"
        
        return url
    
    def _get_site_url(self, url: str) -> str:
        """Get the base site URL for constructing job links."""
        if "/wday/cxs/" in url:
            # Extract from API URL
            match = re.match(r'(https?://[^/]+\.myworkdayjobs\.com)/wday/cxs/[^/]+/([^/]+)', url)
            if match:
                return f"{match.group(1)}/{match.group(2)}"
        
        # Strip query params and trailing slashes
        return url.split('?')[0].rstrip('/')
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from Workday API.
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        offset = 0
        limit = 20
        
        try:
            while True:
                # Workday API accepts empty appliedFacets for all jobs
                payload = {
                    "appliedFacets": {},
                    "limit": limit,
                    "offset": offset,
                    "searchText": ""
                }
                
                self._rate_limit(0.5, 1.5)
                response = self.session.post(
                    self.api_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    },
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                job_postings = data.get("jobPostings", [])
                
                if not job_postings:
                    break
                
                for job_data in job_postings:
                    external_path = job_data.get("externalPath", "")
                    
                    # Construct job URL
                    if external_path:
                        job_url = f"{self.site_url}{external_path}"
                    else:
                        job_url = ""
                    
                    job = Job(
                        company=self.company_name,
                        title=job_data.get("title", ""),
                        url=job_url,
                        location=job_data.get("locationsText", ""),
                        job_type="Full-time",
                        description=""
                    )
                    if job.url and job.title:
                        jobs.append(job)
                
                total = data.get("total", 0)
                if offset + limit >= total or offset >= 200:
                    break
                    
                offset += limit
                
        except requests.RequestException as e:
            logger.error(f"{self.company_name} Workday API error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"{self.company_name} Workday API error: {e}")
        
        logger.info(f"Scraped {len(jobs)} jobs from {self.company_name}")
        return jobs

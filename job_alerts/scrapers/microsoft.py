"""
Microsoft Careers API scraper.
Uses Microsoft's public job search API.
"""

from typing import List
import logging
import json

import requests

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class MicrosoftScraper(BaseScraper):
    """Scraper for Microsoft Careers using their API."""
    
    def __init__(self, base_url: str = "https://gcsservices.careers.microsoft.com"):
        super().__init__(company_name="Microsoft", base_url=base_url)
        self.api_url = "https://gcsservices.careers.microsoft.com/search/api/v1/search"
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from Microsoft's Careers API.
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        page = 1
        page_size = 100
        
        try:
            while True:
                payload = {
                    "lang": "en_us",
                    "country": "us",
                    "page": page,
                    "pageSize": page_size,
                    "sortBy": "postedDate",
                    "sortOrder": "desc"
                }
                
                self._rate_limit(0.5, 1.5)
                response = self.session.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Handle different API response structures
                job_list = data.get("operationResult", {}).get("result", {}).get("jobs", [])
                if not job_list:
                    job_list = data.get("jobs", [])
                
                if not job_list:
                    break
                
                for job_data in job_list:
                    location = job_data.get("location", "")
                    if isinstance(location, list):
                        location = ", ".join(location[:3])
                    elif isinstance(location, dict):
                        location = location.get("city", "") or location.get("country", "")
                    
                    job = Job(
                        company=self.company_name,
                        title=job_data.get("title", ""),
                        url=f"https://careers.microsoft.com/us/en/job/{job_data.get('jobId', '')}",
                        location=location,
                        job_type=job_data.get("employmentType", "Full-time"),
                        description=job_data.get("description", "")[:500] if job_data.get("description") else ""
                    )
                    jobs.append(job)
                
                # Limit pages
                if page >= 5:
                    break
                    
                page += 1
                
        except requests.RequestException as e:
            logger.error(f"Microsoft API error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Microsoft JSON parse error: {e}")
        
        logger.info(f"Scraped {len(jobs)} jobs from Microsoft")
        return jobs

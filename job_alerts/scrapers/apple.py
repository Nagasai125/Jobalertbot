"""
Apple Jobs API scraper.
Uses Apple's public job search API.
"""

from typing import List
import logging
import json

import requests

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class AppleScraper(BaseScraper):
    """Scraper for Apple Jobs using their API."""
    
    def __init__(self, base_url: str = "https://jobs.apple.com"):
        super().__init__(company_name="Apple", base_url=base_url)
        self.api_url = "https://jobs.apple.com/api/role/search"
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from Apple's Jobs API.
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        page = 0
        
        try:
            while True:
                params = {
                    "page": page,
                    "locale": "en-us",
                    "location": "united-states-USA"
                }
                
                self._rate_limit(0.5, 1.5)
                response = self.session.get(
                    self.api_url,
                    params=params,
                    headers={"Accept": "application/json"},
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Apple returns searchResults
                results = data.get("searchResults", [])
                if not results:
                    break
                
                for job_data in results:
                    locations = job_data.get("locations", [])
                    location = ", ".join([loc.get("name", "") for loc in locations[:3]]) if locations else ""
                    
                    job = Job(
                        company=self.company_name,
                        title=job_data.get("postingTitle", ""),
                        url=f"https://jobs.apple.com/en-us/details/{job_data.get('positionId', '')}",
                        location=location,
                        job_type=job_data.get("jobType", {}).get("name", "Full-time") if isinstance(job_data.get("jobType"), dict) else "Full-time",
                        description=""
                    )
                    jobs.append(job)
                
                # Check if there are more pages
                total_records = data.get("totalRecords", 0)
                if (page + 1) * 20 >= total_records or page >= 10:
                    break
                    
                page += 1
                
        except requests.RequestException as e:
            logger.error(f"Apple API error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Apple JSON parse error: {e}")
        
        logger.info(f"Scraped {len(jobs)} jobs from Apple")
        return jobs

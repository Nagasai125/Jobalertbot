"""
Amazon Jobs API scraper.
Uses Amazon's public jobs search API.
"""

from typing import List
import logging
import json

import requests

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class AmazonScraper(BaseScraper):
    """Scraper for Amazon Jobs using their API."""
    
    def __init__(self, base_url: str = "https://www.amazon.jobs/en/search.json"):
        super().__init__(company_name="Amazon", base_url=base_url)
        self.api_url = "https://www.amazon.jobs/en/search.json"
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from Amazon's Jobs API.
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        offset = 0
        limit = 100
        
        try:
            while True:
                params = {
                    "base_query": "",
                    "country": "USA",
                    "result_limit": limit,
                    "offset": offset,
                    "sort": "recent"
                }
                
                self._rate_limit(0.5, 1.5)
                response = self.session.get(self.api_url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                job_list = data.get("jobs", [])
                
                if not job_list:
                    break
                
                for job_data in job_list:
                    job = Job(
                        company=self.company_name,
                        title=job_data.get("title", ""),
                        url=f"https://www.amazon.jobs{job_data.get('job_path', '')}",
                        location=job_data.get("normalized_location", job_data.get("location", "")),
                        job_type=job_data.get("job_category", ""),
                        description=job_data.get("description_short", "")[:500]
                    )
                    jobs.append(job)
                
                # Limit to first 500 jobs to avoid excessive requests
                if offset + limit >= 500:
                    break
                    
                offset += limit
                
        except requests.RequestException as e:
            logger.error(f"Amazon API error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Amazon JSON parse error: {e}")
        
        logger.info(f"Scraped {len(jobs)} jobs from Amazon")
        return jobs

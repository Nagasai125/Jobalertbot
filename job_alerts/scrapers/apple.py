"""
Apple Jobs scraper.
Uses Playwright to render the page and extract job data from hydration state.
"""

from typing import List
import logging
import json
import re

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class AppleScraper(BaseScraper):
    """Scraper for Apple Jobs using Playwright to render the React app."""
    
    def __init__(self, base_url: str = "https://jobs.apple.com"):
        super().__init__(company_name="Apple", base_url=base_url)
        self.search_url = "https://jobs.apple.com/en-us/search?location=united-states-USA"
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from Apple's Jobs page.
        
        Uses Playwright to render the page and extract job data from 
        window.__staticRouterHydrationData which contains the initial job list.
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright not installed. Install with: pip install playwright && playwright install chromium")
            return jobs
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                logger.info(f"Loading Apple careers page: {self.search_url}")
                page.goto(self.search_url, wait_until="networkidle", timeout=60000)
                
                # Extract job data from the hydration state
                job_data = page.evaluate("""
                    () => {
                        if (window.__staticRouterHydrationData && 
                            window.__staticRouterHydrationData.loaderData &&
                            window.__staticRouterHydrationData.loaderData.search) {
                            return window.__staticRouterHydrationData.loaderData.search.searchResults || [];
                        }
                        return [];
                    }
                """)
                
                logger.info(f"Found {len(job_data)} jobs in Apple hydration data")
                
                for item in job_data:
                    try:
                        # Extract location from locations array
                        locations = item.get("locations", [])
                        location = ", ".join([loc.get("name", "") for loc in locations[:3]]) if locations else "United States"
                        
                        # Build job URL
                        position_id = item.get("positionId", "")
                        job_url = f"https://jobs.apple.com/en-us/details/{position_id}" if position_id else ""
                        
                        # Get team/job type
                        team = item.get("team", {})
                        job_type = team.get("teamName", "Full-time") if isinstance(team, dict) else "Full-time"
                        
                        job = Job(
                            company=self.company_name,
                            title=item.get("postingTitle", ""),
                            url=job_url,
                            location=location,
                            job_type=job_type,
                            description=item.get("jobSummary", "")
                        )
                        jobs.append(job)
                    except Exception as e:
                        logger.warning(f"Error parsing Apple job: {e}")
                        continue
                
                browser.close()
                
        except Exception as e:
            logger.error(f"Apple scraper error: {e}")
        
        logger.info(f"Scraped {len(jobs)} jobs from Apple")
        return jobs

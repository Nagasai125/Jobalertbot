"""
Uber Careers scraper using Playwright for JavaScript rendering.
"""

from typing import List
import logging
import re

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class UberScraper(BaseScraper):
    """Scraper for Uber Careers using headless browser."""
    
    def __init__(self, base_url: str = "https://www.uber.com/us/en/careers/list/"):
        """
        Initialize Uber scraper.
        
        Args:
            base_url: Uber careers page URL
        """
        super().__init__(company_name="Uber", base_url=base_url)
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from Uber Careers using Playwright.
        
        Returns:
            List of Job objects found.
        """
        jobs = []
        
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                logger.info(f"Loading Uber Careers page: {self.base_url}")
                
                page.goto(self.base_url, wait_until="networkidle", timeout=30000)
                
                # Wait for job listings to load
                page.wait_for_timeout(3000)
                
                # Look for job cards - Uber uses various structures
                job_cards = page.query_selector_all('[data-testid*="job"], [class*="JobCard"], a[href*="/careers/list/"]')
                
                if not job_cards:
                    # Try alternative selectors
                    job_cards = page.query_selector_all('div[class*="css-"] a[href*="/careers/"]')
                
                logger.info(f"Found {len(job_cards)} potential job elements")
                
                seen_urls = set()
                
                # Get all links that look like job postings
                all_links = page.query_selector_all('a[href*="/careers/list/"]')
                
                for link in all_links:
                    try:
                        href = link.get_attribute('href')
                        if not href or href in seen_urls:
                            continue
                        
                        # Skip navigation links (must have job ID pattern)
                        if not re.search(r'/list/\d+', href) and not re.search(r'/list/[a-f0-9-]+', href):
                            continue
                        
                        # Make absolute URL
                        if href.startswith('/'):
                            href = f"https://www.uber.com{href}"
                        
                        seen_urls.add(href)
                        
                        # Get title from link text or parent
                        title = link.inner_text().strip()
                        
                        # If title is too short, try parent element
                        if len(title) < 5:
                            parent = link.evaluate_handle("el => el.closest('div, li, article')")
                            if parent:
                                title = parent.inner_text().strip().split('\n')[0]
                        
                        if not title or len(title) < 5 or len(title) > 200:
                            continue
                        
                        # Try to find location
                        location = "USA"
                        parent = link.evaluate_handle("el => el.closest('div, li, article')")
                        if parent:
                            parent_text = parent.inner_text()
                            # Look for location patterns
                            loc_match = re.search(r'([\w\s]+,\s*[A-Z]{2})', parent_text)
                            if loc_match:
                                location = loc_match.group(1)
                        
                        job = Job(
                            company=self.company_name,
                            title=title,
                            url=href,
                            location=location,
                            job_type="Full-time",
                            description=""
                        )
                        jobs.append(job)
                        
                    except Exception as e:
                        logger.debug(f"Error parsing job link: {e}")
                        continue
                
                # Scroll to load more jobs
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)
                
                browser.close()
                
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        except Exception as e:
            logger.error(f"Uber scraper error: {e}")
        
        logger.info(f"Scraped {len(jobs)} jobs from {self.company_name}")
        return jobs

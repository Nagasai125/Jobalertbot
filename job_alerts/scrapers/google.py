"""
Google Careers scraper using Playwright for JavaScript rendering.
"""

from typing import List
import logging
import re

from .base import BaseScraper
from ..database import Job

logger = logging.getLogger(__name__)


class GoogleScraper(BaseScraper):
    """Scraper for Google Careers using headless browser."""
    
    def __init__(self, base_url: str = "https://www.google.com/about/careers/applications/jobs/results"):
        """
        Initialize Google scraper.
        
        Args:
            base_url: Google careers page URL
        """
        super().__init__(company_name="Google", base_url=base_url)
    
    def scrape(self) -> List[Job]:
        """
        Scrape job listings from Google Careers using Playwright.
        
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
                
                # Add US location filter
                url = f"{self.base_url}?location=United%20States"
                logger.info(f"Loading Google Careers page: {url}")
                
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Wait for job listings to load - these are the actual job card classes
                page.wait_for_selector('li[class*="lLd3Je"], [class*="sMn82b"]', timeout=15000)
                
                # Give extra time for dynamic content
                page.wait_for_timeout(2000)
                
                # Get job cards
                job_cards = page.query_selector_all('li[class*="lLd3Je"]')
                logger.info(f"Found {len(job_cards)} job cards")
                
                seen_urls = set()
                
                for card in job_cards:
                    try:
                        # Get the link element
                        link = card.query_selector('a')
                        if not link:
                            continue
                        
                        href = link.get_attribute('href')
                        if not href or href in seen_urls:
                            continue
                        
                        # Make absolute URL
                        if href.startswith('./'):
                            href = f"https://www.google.com/about/careers/applications/{href[2:]}"
                        elif href.startswith('/'):
                            href = f"https://www.google.com{href}"
                        
                        seen_urls.add(href)
                        
                        # Get full text and parse it
                        full_text = card.inner_text().strip()
                        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                        
                        # First line is usually the title
                        title = lines[0] if lines else ""
                        
                        # Skip if not a real job title
                        if not title or len(title) < 5 or title in ['corporate_fare', 'Google', 'place']:
                            continue
                        
                        # Find location - usually contains city/state/country
                        location = ""
                        for line in lines[1:]:
                            if any(loc in line.lower() for loc in ['usa', 'united states', 'remote', 'ca,', 'ny,', 'wa,']):
                                location = line
                                break
                        
                        if not location and len(lines) > 2:
                            location = lines[2] if 'Google' not in lines[2] else "United States"
                        
                        # Clean up location (remove icons like 'place', 'corporate_fare')
                        location = re.sub(r'^(place|corporate_fare|bar_chart)\s*', '', location)
                        location = location.strip()
                        
                        job = Job(
                            company=self.company_name,
                            title=title,
                            url=href,
                            location=location or "United States",
                            job_type="Full-time",
                            description=""
                        )
                        jobs.append(job)
                        
                    except Exception as e:
                        logger.debug(f"Error parsing job card: {e}")
                        continue
                
                # Try to load more jobs by scrolling
                if len(jobs) >= 20:
                    try:
                        for _ in range(3):  # Scroll 3 times to load more
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            page.wait_for_timeout(2000)
                            
                            # Check for new cards
                            new_cards = page.query_selector_all('li[class*="lLd3Je"]')
                            if len(new_cards) > len(job_cards):
                                for card in new_cards[len(job_cards):]:
                                    try:
                                        link = card.query_selector('a')
                                        if not link:
                                            continue
                                        href = link.get_attribute('href')
                                        if not href or href in seen_urls:
                                            continue
                                        
                                        if href.startswith('./'):
                                            href = f"https://www.google.com/about/careers/applications/{href[2:]}"
                                        elif href.startswith('/'):
                                            href = f"https://www.google.com{href}"
                                        
                                        seen_urls.add(href)
                                        
                                        full_text = card.inner_text().strip()
                                        lines = [l.strip() for l in full_text.split('\n') if l.strip()]
                                        title = lines[0] if lines else ""
                                        
                                        if not title or len(title) < 5:
                                            continue
                                        
                                        location = ""
                                        for line in lines[1:]:
                                            if any(loc in line.lower() for loc in ['usa', 'united states', 'remote', 'ca,', 'ny,']):
                                                location = line
                                                break
                                        
                                        location = re.sub(r'^(place|corporate_fare|bar_chart)\s*', '', location).strip()
                                        
                                        job = Job(
                                            company=self.company_name,
                                            title=title,
                                            url=href,
                                            location=location or "United States",
                                            job_type="Full-time",
                                            description=""
                                        )
                                        jobs.append(job)
                                    except:
                                        continue
                                
                                job_cards = new_cards
                    except Exception as e:
                        logger.debug(f"Error during scroll: {e}")
                
                browser.close()
                
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        except Exception as e:
            logger.error(f"Google scraper error: {e}")
        
        logger.info(f"Scraped {len(jobs)} jobs from {self.company_name}")
        return jobs

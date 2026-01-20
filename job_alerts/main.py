"""
Main entry point for Job Alerts system.
Orchestrates scraping, matching, deduplication, and notifications.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Dict, Type

from dotenv import load_dotenv
load_dotenv()  # Load .env file before importing config

from .config import load_config, Config
from .database import JobDatabase, Job
from .scheduler import JobScheduler
from .scrapers import (
    BaseScraper, GitHubScraper, StripeScraper, GenericScraper,
    AmazonScraper, AppleScraper, MicrosoftScraper, WorkdayScraper,
    GoogleScraper, UberScraper, OracleScraper
)
from .matchers import KeywordMatcher
from .notifiers import BaseNotifier, TelegramNotifier, EmailNotifier


# Scraper registry
SCRAPERS: Dict[str, Type[BaseScraper]] = {
    'github': GitHubScraper,
    'stripe': StripeScraper,
    'generic': GenericScraper,
    'amazon': AmazonScraper,
    'apple': AppleScraper,
    'microsoft': MicrosoftScraper,
    'workday': WorkdayScraper,
    'google': GoogleScraper,
    'uber': UberScraper,
    'oracle': OracleScraper,
}


def setup_logging(config: Config):
    """Configure logging based on config."""
    log_dir = Path(config.logging.file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, config.logging.level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.logging.file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def create_scrapers(config: Config) -> List[BaseScraper]:
    """Create scraper instances based on config."""
    scrapers = []
    
    for company in config.companies:
        scraper_type = company.scraper.lower()
        
        if scraper_type in SCRAPERS:
            # Scrapers that need company_name parameter
            if scraper_type in ('generic', 'workday'):
                scraper = SCRAPERS[scraper_type](
                    company_name=company.name,
                    base_url=company.url
                )
            else:
                scraper = SCRAPERS[scraper_type](base_url=company.url)
            scrapers.append(scraper)
        else:
            logging.warning(f"Unknown scraper type '{scraper_type}' for {company.name}")
    
    return scrapers


def create_notifiers(config: Config) -> List[BaseNotifier]:
    """Create notifier instances based on config."""
    notifiers = []
    
    if config.notifications.telegram.enabled:
        notifiers.append(TelegramNotifier(config.notifications.telegram))
    
    if config.notifications.email.enabled:
        notifiers.append(EmailNotifier(config.notifications.email))
    
    return notifiers


def run_job_check(
    scrapers: List[BaseScraper],
    matcher: KeywordMatcher,
    database: JobDatabase,
    notifiers: List[BaseNotifier]
):
    """
    Run a single job check cycle.
    
    1. Scrape all company career pages
    2. Filter jobs by keywords
    3. Deduplicate and store new jobs
    4. Send notifications for new matching jobs
    """
    logger = logging.getLogger(__name__)
    
    all_jobs: List[Job] = []
    
    # Step 1: Scrape
    for scraper in scrapers:
        try:
            jobs = scraper.scrape()
            all_jobs.extend(jobs)
            logger.info(f"Scraped {len(jobs)} jobs from {scraper.company_name}")
        except Exception as e:
            logger.error(f"Scraper error for {scraper.company_name}: {e}")
    
    logger.info(f"Total jobs scraped: {len(all_jobs)}")
    
    # Step 2: Filter by keywords
    matching_jobs = [job for job in all_jobs if matcher.matches(job)]
    logger.info(f"Jobs matching keywords: {len(matching_jobs)}")
    
    # Step 3: Deduplicate and store
    new_jobs: List[Job] = []
    for job in matching_jobs:
        if database.add_job(job):
            new_jobs.append(job)
    
    logger.info(f"New jobs found: {len(new_jobs)}")
    
    if not new_jobs:
        logger.info("No new jobs to notify about.")
        return
    
    # Step 4: Send notifications
    for notifier in notifiers:
        try:
            count = notifier.send_batch(new_jobs)
            logger.info(f"{notifier.name}: Notified for {count} jobs")
            
            # Mark as notified
            for job in new_jobs:
                database.mark_notified(job)
        except Exception as e:
            logger.error(f"Notification error ({notifier.name}): {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Job Alert Notification System')
    parser.add_argument(
        '-c', '--config',
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (no scheduling)'
    )
    parser.add_argument(
        '--test-scrape',
        action='store_true',
        help='Test scraping only, print jobs to console'
    )
    parser.add_argument(
        '--test-notify',
        action='store_true',
        help='Send a test notification'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)
    logger.info("Job Alerts starting...")
    
    # Create components
    scrapers = create_scrapers(config)
    matcher = KeywordMatcher(config.keywords, config.matching)
    database = JobDatabase(config.database.path)
    notifiers = create_notifiers(config)
    
    logger.info(f"Configured {len(scrapers)} scrapers, {len(notifiers)} notifiers")
    
    # Handle test modes
    if args.test_scrape:
        logger.info("Test scrape mode - printing jobs to console")
        for scraper in scrapers:
            jobs = scraper.scrape()
            print(f"\n=== {scraper.company_name} ({len(jobs)} jobs) ===")
            for job in jobs:
                match = "✓" if matcher.matches(job) else "✗"
                print(f"  [{match}] {job.title}")
                print(f"      Location: {job.location}")
                print(f"      URL: {job.url}")
        sys.exit(0)
    
    if args.test_notify:
        logger.info("Test notify mode - sending test notification")
        test_job = Job(
            company="Test Company",
            title="Software Engineer",
            url="https://example.com/jobs/123",
            location="Remote",
            job_type="Full-time",
            description="This is a test job posting."
        )
        for notifier in notifiers:
            if notifier.send(test_job):
                print(f"✓ {notifier.name} notification sent successfully")
            else:
                print(f"✗ {notifier.name} notification failed")
        sys.exit(0)
    
    # Define the job check function
    def job_check():
        run_job_check(scrapers, matcher, database, notifiers)
    
    # Run
    scheduler = JobScheduler(config.polling.interval_minutes)
    
    if args.once:
        scheduler.run_once(job_check)
    else:
        scheduler.start(job_check)
    
    # Cleanup
    database.close()


if __name__ == '__main__':
    main()

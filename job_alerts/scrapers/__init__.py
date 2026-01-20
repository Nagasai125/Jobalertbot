# Scrapers Package
from .base import BaseScraper
from .github import GitHubScraper
from .stripe import StripeScraper
from .generic import GenericScraper
from .amazon import AmazonScraper
from .apple import AppleScraper
from .microsoft import MicrosoftScraper
from .workday import WorkdayScraper
from .google import GoogleScraper
from .uber import UberScraper
from .oracle import OracleScraper

__all__ = [
    'BaseScraper', 
    'GitHubScraper', 
    'StripeScraper', 
    'GenericScraper',
    'AmazonScraper',
    'AppleScraper',
    'MicrosoftScraper',
    'WorkdayScraper',
    'GoogleScraper',
    'UberScraper',
    'OracleScraper'
]


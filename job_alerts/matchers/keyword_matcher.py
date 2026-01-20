"""
Keyword matching logic for job filtering.
Supports exact, tokenized, and fuzzy matching.
"""

from typing import List, Set
import logging
import re

from rapidfuzz import fuzz

from ..database import Job
from ..config import KeywordsConfig, MatchingConfig, FiltersConfig

logger = logging.getLogger(__name__)


class KeywordMatcher:
    """
    Matches jobs against configured keywords.
    
    Supports three matching modes:
    - exact: Case-insensitive substring match
    - tokenized: Match base keywords, ignore modifiers (numbers, suffixes)
    - fuzzy: Similarity-based matching with configurable threshold
    """
    
    def __init__(self, keywords: KeywordsConfig, matching: MatchingConfig, filters: FiltersConfig = None):
        """
        Initialize the keyword matcher.
        
        Args:
            keywords: Keyword configuration (include, exclude, locations).
            matching: Matching algorithm configuration.
            filters: Filter configuration (experience).
        """
        self.keywords = keywords
        self.matching = matching
        self.filters = filters
        
        # Pre-process keywords for faster matching
        self._include_keywords = self._normalize_keywords(keywords.include)
        self._exclude_keywords = self._normalize_keywords(keywords.exclude)
        self._location_keywords = self._normalize_keywords(keywords.locations)
        
        # Experience level keywords map
        self.EXPERIENCE_LEVELS = {
            'intern': ['intern', 'internship', 'co-op', 'student', 'university'],
            'entry': ['entry', 'junior', 'associate', 'grad', 'new grad', '0-1', '0-2'],
            'mid': ['mid', 'intermediate', 'staff', 'ii', 'iii'],
            'senior': ['senior', 'sr', 'lead', 'principal', 'head', 'iv', 'v', 'manager', 'director']
        }
        
    def _normalize_keywords(self, keywords: List[str]) -> Set[str]:
        """Normalize keywords for matching."""
        if self.matching.case_sensitive:
            return set(keywords)
        return {kw.lower() for kw in keywords}
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for matching."""
        if not self.matching.case_sensitive:
            text = text.lower()
        return text
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text for tokenized matching.
        Removes numbers and common suffixes like I, II, III, 1, 2, 3.
        """
        # Remove numbers and roman numerals at end
        text = re.sub(r'\s+(I{1,3}|IV|V|VI{0,3}|[0-9]+)$', '', text, flags=re.IGNORECASE)
        # Remove special characters but keep spaces
        text = re.sub(r'[^\w\s]', ' ', text)
        # Split into tokens
        return text.split()
    
    def _exact_match(self, text: str, keywords: Set[str]) -> bool:
        """Check if any keyword is a substring of text."""
        normalized = self._normalize_text(text)
        for keyword in keywords:
            if keyword in normalized:
                return True
        return False
    
    def _tokenized_match(self, text: str, keywords: Set[str]) -> bool:
        """
        Check if keywords match after tokenization.
        'Software Engineer' matches 'Software Engineer Chrome Extension'
        """
        normalized = self._normalize_text(text)
        
        for keyword in keywords:
            # Check if all tokens in keyword are present in text
            keyword_tokens = self._tokenize(keyword)
            text_tokens = self._tokenize(normalized)
            
            # Simple containment check
            if all(kt in normalized for kt in keyword_tokens):
                return True
            
            # Check if keyword tokens appear consecutively
            keyword_str = ' '.join(keyword_tokens)
            text_str = ' '.join(text_tokens)
            if keyword_str in text_str:
                return True
        
        return False
    
    def _fuzzy_match(self, text: str, keywords: Set[str]) -> bool:
        """
        Check if text fuzzy-matches any keyword.
        Uses token_set_ratio for better partial matching.
        """
        normalized = self._normalize_text(text)
        threshold = self.matching.fuzzy_threshold * 100  # rapidfuzz uses 0-100
        
        for keyword in keywords:
            # Token set ratio handles word order and extra words well
            ratio = fuzz.token_set_ratio(keyword, normalized)
            if ratio >= threshold:
                logger.debug(f"Fuzzy match: '{keyword}' ~ '{text}' (score: {ratio})")
                return True
        
        return False

    def _check_experience(self, job: Job) -> bool:
        """
        Check if job matches experience level filter.
        If no experience filter is set, allow all.
        If job text matches any allowed level keyword, allow it.
        If job text matches any DISALLOWED level keyword, block it.
        Default to allowing if ambiguous.
        """
        if not self.filters or not self.filters.experience:
            return True
            
        allowed_levels = set(l.lower() for l in self.filters.experience)
        if not allowed_levels:
            return True

        title_lower = job.title.lower()
        
        # Check against each defined level
        detected_levels = set()
        for level, keywords in self.EXPERIENCE_LEVELS.items():
            if any(k in title_lower for k in keywords):
                detected_levels.add(level)
        
        # If no specific level detected, assume it fits (or check description - optional)
        if not detected_levels:
            # Logic: If looking for 'entry', avoiding 'senior' is key.
            # If no level words found, it's likely a generic title like "Software Engineer" which fits all.
            return True
            
        # If we detected levels, check if ANY of them are allowed
        # e.g. "Senior Software Engineer" -> detected 'senior' -> if allowed_levels has 'senior', return True
        return any(pk in allowed_levels for pk in detected_levels)

    def matches(self, job: Job) -> bool:
        """
        Check if a job matches the configured keywords.
        
        Args:
            job: The Job to check.
            
        Returns:
            True if the job matches, False otherwise.
        """
        # If no include keywords, match all
        if not self._include_keywords:
            return True
        
        # Check exclusions first
        if self._exclude_keywords:
            text_to_check = f"{job.title} {job.description}"
            if self._matches_any(text_to_check, self._exclude_keywords):
                logger.debug(f"Job excluded by keyword: {job.title}")
                return False
        
        # Check location filter
        if self._location_keywords and job.location:
            if not self._matches_any(job.location, self._location_keywords):
                logger.debug(f"Job excluded by location: {job.title} ({job.location})")
                return False

        # Check experience filter
        if not self._check_experience(job):
            logger.debug(f"Job excluded by experience level: {job.title}")
            return False
        
        # Check include keywords against title and description
        text_to_check = f"{job.title} {job.description}"
        return self._matches_any(text_to_check, self._include_keywords)
    
    def _matches_any(self, text: str, keywords: Set[str]) -> bool:
        """Check if text matches any keyword using configured mode."""
        mode = self.matching.mode
        
        if mode == "exact":
            return self._exact_match(text, keywords)
        elif mode == "tokenized":
            return self._tokenized_match(text, keywords)
        elif mode == "fuzzy":
            # Try tokenized first, then fuzzy for better performance
            if self._tokenized_match(text, keywords):
                return True
            return self._fuzzy_match(text, keywords)
        else:
            logger.warning(f"Unknown matching mode: {mode}, falling back to tokenized")
            return self._tokenized_match(text, keywords)

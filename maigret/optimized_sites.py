"""
Optimized sites module for Maigret.
This module provides faster site loading, caching, and indexing.
"""

import copy
import json
import os
import sys
import time
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple, Any, Iterator
import re

from .utils import CaseConverter, URLMatcher, is_country_tag


class OptimizedMaigretSite:
    """
    Memory-efficient version of MaigretSite with performance optimizations.
    """
    
    __slots__ = (
        'name', 'url_main', 'url', 'check_type', 'tags', 'presense_strs', 
        'absence_strs', 'stats', 'engine', 'alexa_rank', 'source', 'protocol',
        'headers', 'url_regexp', 'regex_check', 'url_probe', 'type', 'ignore403',
        'activation', 'get_params', 'request_head_only', 'errors', 'disabled',
        'similar_search', 'url_subpath', 'engine_data', 'engine_obj'
    )
    
    def __init__(self, name, information):
        """
        Initialize site with optimized memory usage.
        
        Args:
            name: Site name
            information: Site metadata dictionary
        """
        self.name = name
        self.url_subpath = ""
        self.alexa_rank = sys.maxsize
        
        # Initialize attributes from information dict
        for k, v in information.items():
            setattr(self, CaseConverter.camel_to_snake(k), v)
        
        # Ensure required attributes exist
        for attr in self.__slots__:
            if not hasattr(self, attr):
                setattr(self, attr, None)
        
        # Initialize containers
        if not self.tags:
            self.tags = []
        if not self.presense_strs:
            self.presense_strs = []
        if not self.absence_strs:
            self.absence_strs = []
        if not self.headers:
            self.headers = {}
        if not self.errors:
            self.errors = {}
        if not self.stats:
            self.stats = {}
        if not self.get_params:
            self.get_params = {}
        if not self.activation:
            self.activation = {}
        
        # Compile URL regexp once at initialization
        self.update_detectors()
    
    def __str__(self):
        """String representation of the site."""
        return f"{self.name} ({self.url_main})"
    
    def update_detectors(self):
        """Update URL detection patterns with cached compilation."""
        if hasattr(self, 'url') and self.url:
            url = self.url
            for group in ["urlMain", "urlSubpath"]:
                snake_case = CaseConverter.camel_to_snake(group)
                if group in url and hasattr(self, snake_case):
                    url = url.replace(
                        "{" + group + "}", 
                        getattr(self, snake_case) or ""
                    )
            
            self.url_regexp = URLMatcher.make_profile_url_regexp(
                url, self.regex_check)
    
    @lru_cache(maxsize=128)
    def detect_username(self, url: str) -> Optional[str]:
        """
        Extract username from URL with caching.
        
        Args:
            url: Profile URL to extract username from
            
        Returns:
            Extracted username or None
        """
        if not self.url_regexp:
            return None
        
        match_groups = self.url_regexp.match(url)
        if match_groups:
            return match_groups.groups()[-1].rstrip("/")
        
        return None
    
    def extract_id_from_url(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Extract ID and type from URL.
        
        Args:
            url: URL to extract from
            
        Returns:
            Tuple of (id, type) or None
        """
        if not self.url_regexp:
            return None
        
        match_groups = self.url_regexp.match(url)
        if not match_groups:
            return None
        
        _id = match_groups.groups()[-1].rstrip("/")
        _type = self.type or "username"
        
        return _id, _type
    
    @property
    def pretty_name(self):
        """Get formatted site name."""
        if self.source:
            return f"{self.name} [{self.source}]"
        return self.name
    
    @property
    def errors_dict(self):
        """Get errors as dictionary with better default handling."""
        return self.errors or {}


class OptimizedMaigretDatabase:
    """
    Optimized database for site management with faster lookups and processing.
    """
    
    def __init__(self, logger=None):
        """
        Initialize the optimized database.
        
        Args:
            logger: Logger instance
        """
        self.sites = {}
        self.engines = {}
        self.logger = logger
        
        # Indexes for faster lookups
        self._tags_index = {}
        self._domain_index = {}
        self._popularity_index = []
        
        # Stats
        self.load_time = 0
        self.site_count = 0
    
    def _extract_domain(self, url_main):
        """Extract domain from main URL."""
        if not url_main or '://' not in url_main:
            return None
        
        try:
            domain = url_main.split('/')[2]
            return domain
        except:
            return None
    
    def _update_indexes(self, site):
        """Update all lookup indexes for a site."""
        # Update tags index
        for tag in site.tags:
            if tag not in self._tags_index:
                self._tags_index[tag] = set()
            self._tags_index[tag].add(site.name)
        
        # Update domain index
        domain = self._extract_domain(site.url_main)
        if domain:
            if domain not in self._domain_index:
                self._domain_index[domain] = set()
            self._domain_index[domain].add(site.name)
        
        # Update popularity index
        if hasattr(site, 'alexa_rank') and site.alexa_rank:
            rank = site.alexa_rank
            # Binary search to find insertion point for rank
            left, right = 0, len(self._popularity_index)
            while left < right:
                mid = (left + right) // 2
                if self._popularity_index[mid][0] < rank:
                    left = mid + 1
                else:
                    right = mid
            
            # Insert site at the correct position
            self._popularity_index.insert(left, (rank, site.name))
    
    def add_site(self, site):
        """
        Add a site to the database and update indexes.
        
        Args:
            site: Site object to add
        """
        self.sites[site.name] = site
        self._update_indexes(site)
        self.site_count += 1
    
    def load_engines(self, engines_data):
        """
        Load engines data.
        
        Args:
            engines_data: Dictionary of engine configurations
        """
        from .maigret import MaigretEngine
        
        for engine_name, engine_data in engines_data.items():
            self.engines[engine_name] = MaigretEngine(engine_name, engine_data)
    
    def load_from_json(self, json_file):
        """
        Load sites data from JSON with optimized processing.
        
        Args:
            json_file: Path to JSON data file
        """
        start_time = time.time()
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Load engines first
        self.load_engines(data.get("engines", {}))
        
        # Process sites in chunks for better memory management
        sites = data.get("sites", {})
        
        # Prepare site objects
        for site_name, site_data in sites.items():
            site = OptimizedMaigretSite(site_name, site_data)
            
            # Set engine if applicable
            if site.engine and site.engine in self.engines:
                site.engine_obj = self.engines[site.engine]
                site.engine_data = site.engine_data or {}
            
            self.add_site(site)
        
        self.load_time = time.time() - start_time
    
    def get_site(self, site_name):
        """
        Get a site by name.
        
        Args:
            site_name: Name of the site
            
        Returns:
            Site object or None
        """
        return self.sites.get(site_name)
    
    def get_sites_by_tag(self, tag):
        """
        Get sites with a specific tag.
        
        Args:
            tag: Tag to filter by
            
        Returns:
            List of matching site objects
        """
        site_names = self._tags_index.get(tag, set())
        return [self.sites[name] for name in site_names if name in self.sites]
    
    def get_sites_by_domain(self, domain):
        """
        Get sites with a specific domain.
        
        Args:
            domain: Domain to filter by
            
        Returns:
            List of matching site objects
        """
        site_names = self._domain_index.get(domain, set())
        return [self.sites[name] for name in site_names if name in self.sites]
    
    def get_popular_sites(self, count=500):
        """
        Get most popular sites by Alexa rank.
        
        Args:
            count: Number of sites to return
            
        Returns:
            List of site objects sorted by popularity
        """
        popular_sites = []
        for _, site_name in self._popularity_index[:count]:
            if site_name in self.sites:
                popular_sites.append(self.sites[site_name])
        return popular_sites
    
    def get_all_sites(self):
        """Get all sites in the database."""
        return list(self.sites.values())
    
    def extract_ids_from_url(self, url):
        """
        Extract IDs from URL across all sites.
        
        Args:
            url: URL to extract from
            
        Returns:
            Dictionary of extracted IDs and their types
        """
        results = {}
        
        # First try to match by domain for better performance
        domain = self._extract_domain(url)
        if domain:
            sites_to_check = self.get_sites_by_domain(domain)
        else:
            sites_to_check = self.get_all_sites()
        
        # Check each site
        for site in sites_to_check:
            id_data = site.extract_id_from_url(url)
            if id_data:
                _id, _type = id_data
                results[_id] = _type
        
        return results


# Lazy loading singleton for the database
class LazyMaigretDatabase:
    """
    Lazy-loading singleton for the Maigret site database.
    Only loads data when needed to conserve memory.
    """
    
    _instance = None
    _initialized = False
    
    @classmethod
    def get_instance(cls, json_file=None):
        """
        Get or create the database instance.
        
        Args:
            json_file: Optional JSON file path to load
            
        Returns:
            OptimizedMaigretDatabase instance
        """
        if cls._instance is None:
            cls._instance = OptimizedMaigretDatabase()
            cls._initialized = False
        
        if json_file and not cls._initialized:
            cls._instance.load_from_json(json_file)
            cls._initialized = True
        
        return cls._instance
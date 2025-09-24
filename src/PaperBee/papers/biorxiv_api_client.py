"""
Direct bioRxiv API client to bypass medRxiv web scraping issues in GitHub Actions.

The findpapers library uses web scraping via www.medrxiv.org which gets blocked (403)
in GitHub Actions, but api.biorxiv.org works perfectly. This module provides direct
API access for bioRxiv papers.
"""

import json
import requests
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from logging import Logger


class BioRxivAPIClient:
    """Direct bioRxiv API client for GitHub Actions compatibility."""
    
    def __init__(self, logger: Optional[Logger] = None):
        self.base_url = "https://api.biorxiv.org"
        self.logger = logger
        
    def search_papers(
        self, 
        query: str, 
        since_date: date, 
        until_date: date, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search bioRxiv papers using the direct API.
        
        Args:
            query: Search query (not used by API, but kept for compatibility)
            since_date: Start date for search
            until_date: End date for search
            limit: Maximum number of papers to return
            
        Returns:
            List of paper dictionaries in findpapers-compatible format
        """
        papers = []
        
        try:
            if self.logger:
                self.logger.info(f"🧬 BioRxiv API: Searching from {since_date} to {until_date}")
            
            # Format dates for API
            since_str = since_date.strftime('%Y-%m-%d')
            until_str = until_date.strftime('%Y-%m-%d')
            
            # Call bioRxiv API endpoint
            url = f"{self.base_url}/details/biorxiv/{since_str}/{until_str}"
            
            if self.logger:
                self.logger.info(f"🔗 BioRxiv API URL: {url}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'collection' in data and data['collection']:
                raw_papers = data['collection'][:limit]  # Limit results
                
                if self.logger:
                    self.logger.info(f"📄 BioRxiv API found {len(raw_papers)} papers")
                
                # Convert to findpapers-compatible format
                for paper in raw_papers:
                    converted_paper = self._convert_to_findpapers_format(paper)
                    if converted_paper:
                        papers.append(converted_paper)
                        
                # Filter by query if specified (simple text search)
                if query and query.strip():
                    papers = self._filter_by_query(papers, query)
                    
            else:
                if self.logger:
                    self.logger.info("📄 BioRxiv API returned no papers")
                    
        except requests.exceptions.RequestException as e:
            if self.logger:
                self.logger.error(f"❌ BioRxiv API request failed: {e}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ BioRxiv API error: {e}")
                
        return papers
    
    def _convert_to_findpapers_format(self, paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert bioRxiv API format to findpapers format."""
        try:
            # Extract DOI
            doi = paper.get('doi', '')
            if not doi:
                return None
                
            # Create findpapers-compatible paper
            converted = {
                'title': paper.get('title', '').strip(),
                'abstract': paper.get('abstract', '').strip(),
                'authors': paper.get('authors', ''),
                'doi': doi,
                'publication_date': paper.get('date', ''),
                'journal': 'bioRxiv',
                'database': 'bioRxiv',
                'url': f"https://www.biorxiv.org/content/{doi}",
                'paper_type': paper.get('type', 'preprint'),
                'category': paper.get('category', ''),
                'license': paper.get('license', ''),
                # Additional bioRxiv specific fields
                'author_corresponding': paper.get('author_corresponding', ''),
                'author_corresponding_institution': paper.get('author_corresponding_institution', ''),
                'version': paper.get('version', '1'),
                'jatsxml': paper.get('jatsxml', '')
            }
            
            return converted
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Error converting paper: {e}")
            return None
    
    def _filter_by_query(self, papers: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Simple text-based filtering by query."""
        if not query or not query.strip():
            return papers
            
        # Extract search terms from query (remove brackets and OR operators)
        search_terms = []
        query_clean = query.replace('[', '').replace(']', '').replace('"', '')
        
        # Split by OR and AND operators
        for term in query_clean.split(' OR '):
            for subterm in term.split(' AND '):
                clean_term = subterm.strip().lower()
                if clean_term and clean_term not in ['or', 'and']:
                    search_terms.append(clean_term)
        
        if not search_terms:
            return papers
            
        filtered_papers = []
        for paper in papers:
            # Search in title and abstract
            text_to_search = (
                paper.get('title', '').lower() + ' ' + 
                paper.get('abstract', '').lower() + ' ' +
                paper.get('category', '').lower()
            )
            
            # Check if any search term matches
            for term in search_terms:
                if term in text_to_search:
                    filtered_papers.append(paper)
                    break  # Found match, move to next paper
                    
        if self.logger and len(filtered_papers) != len(papers):
            self.logger.info(f"🔍 BioRxiv query '{query}' filtered {len(papers)} → {len(filtered_papers)} papers")
            
        return filtered_papers
#!/usr/bin/env python3
"""
Direct bioRxiv API Test - Test the new BioRxivAPIClient integration
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add src to path for local imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PaperBee.papers.biorxiv_api_client import BioRxivAPIClient
from PaperBee.papers.papers_finder import PapersFinder

def test_direct_api():
    """Test direct bioRxiv API client"""
    print("🧬 Testing Direct bioRxiv API Client")
    print("=" * 50)
    
    client = BioRxivAPIClient()
    
    # Test query - using same as GitHub Actions workflow
    query = "computational biology"
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    
    print(f"📋 Query: {query}")
    print(f"📅 Date range: {start_date.date()} to {end_date.date()}")
    
    try:
        papers = client.search_papers(
            query=query,
            since_date=start_date,
            until_date=end_date,
            limit=10
        )
        
        print(f"✅ Found {len(papers)} papers")
        
        if papers:
            print("\n📄 Sample paper:")
            paper = papers[0]
            print(f"   Title: {paper.get('title', 'N/A')[:80]}...")
            print(f"   Authors: {', '.join(paper.get('authors', [])[:3])}")
            print(f"   Date: {paper.get('publication_date', 'N/A')}")
            print(f"   DOI: {paper.get('doi', 'N/A')}")
        
        return len(papers)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

def test_papers_finder_integration():
    """Test the integrated PapersFinder with bioRxiv"""
    print("\n🔍 Testing PapersFinder Integration")
    print("=" * 50)
    
    # Create minimal config for testing
    config = {
        'databases': ['biorxiv'],
        'query_biorxiv': 'computational biology',  # Same as GitHub Actions
        'since': 7,  # days ago
        'limit': 10,
        'limit_per_database': 10,
        'output_dir': '/tmp/paperbee_test',
    }
    
    # Create output directory
    os.makedirs(config['output_dir'], exist_ok=True)
    
    try:
        finder = PapersFinder(
            root_dir=config['output_dir'],
            spreadsheet_id="dummy_spreadsheet_id",
            google_credentials_json="dummy_creds.json",
            sheet_name="dummy_sheet",
            databases=config['databases'],
            query_biorxiv=config['query_biorxiv'],  # Use specific bioRxiv query
            # query="machine learning",  # Don't use unified query for this test
            since=config['since']
        )
        
        papers = finder.find_and_process_papers()
        print(f"✅ PapersFinder found {len(papers)} papers")
        
        # Check if bioRxiv file was created
        biorxiv_file = os.path.join(config['output_dir'], f"{finder.today_str}_biorxiv.json")
        if os.path.exists(biorxiv_file):
            with open(biorxiv_file, 'r') as f:
                biorxiv_data = json.load(f)
                print(f"📁 bioRxiv file contains {len(biorxiv_data.get('papers', []))} papers")
                if 'metadata' in biorxiv_data:
                    print(f"📊 API method: {biorxiv_data['metadata'].get('api_method', 'unknown')}")
        
        return len(papers)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    print("🚀 Direct bioRxiv API Integration Test")
    print("=" * 60)
    
    # Test 1: Direct API
    api_count = test_direct_api()
    
    # Test 2: Integrated PapersFinder
    finder_count = test_papers_finder_integration()
    
    print("\n📊 Results Summary")
    print("=" * 30)
    print(f"Direct API: {api_count} papers")
    print(f"PapersFinder: {finder_count} papers")
    
    if api_count > 0 and finder_count > 0:
        print("✅ Both tests successful!")
    else:
        print("❌ Some tests failed")
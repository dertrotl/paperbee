#!/usr/bin/env python3
"""
Einfacher Test um zu sehen, warum MarrPeng bioRxiv Suche fehlschlägt
"""

import asyncio
import sys
from datetime import datetime, timedelta
import os

# Set environment for testing
os.environ['GOOGLE_SPREADSHEET_ID'] = 'dummy_test_id'
os.environ['GOOGLE_CREDENTIALS_JSON'] = './dummy_google_creds.json'
os.environ['NCBI_API_KEY'] = 'dummy_ncbi_key'

sys.path.insert(0, "./src")

from PaperBee.papers.papers_finder import PapersFinder

async def test_marrpeng_queries():
    print("🧪 TESTING MarrPeng Queries")
    print("=" * 60)
    
    # MarrPeng Happy Pixels queries
    biorxiv_query = "[computational pathology] OR [cell segmentation] OR [microscopy] OR [biomedical imaging] OR [machine learning] OR [deep learning] OR [computer vision] OR [cell detection] OR [foundation models] OR [vision language model] OR [holography] OR [organoid]"
    
    pubmed_query = "[computational pathology] OR [cell segmentation] OR [microscopy image analysis] OR [biomedical image analysis] OR [deep learning medical] OR [machine learning pathology] OR [foundation models] OR [vision language model] OR [multimodal AI] OR [holography] OR [organoid detection]"
    
    config = {
        'GOOGLE_SPREADSHEET_ID': 'dummy_test_id',
        'GOOGLE_CREDENTIALS_JSON': './dummy_google_creds.json',
        'NCBI_API_KEY': 'dummy_ncbi_key',
        'LOCAL_ROOT_DIR': '.',
        'databases': ['pubmed', 'biorxiv'],
        'query_biorxiv': biorxiv_query,
        'query_pubmed_arxiv': pubmed_query,
        'limit': 50,
        'limit_per_database': 25,
        'LLM_FILTERING': False,  # Disable LLM for pure search test
        'SLACK': {'is_posting_on': False},
        'TELEGRAM': {'is_posting_on': False},
        'ZULIP': {'is_posting_on': False}
    }
    
    print(f"🧬 bioRxiv Query: {biorxiv_query[:100]}...")
    print(f"📄 PubMed Query: {pubmed_query[:100]}...")
    print(f"📅 Search window: 1 day back")
    print()
    
    try:
        finder = PapersFinder(config)
        
        # Test the search
        print("🔍 Starting paper search...")
        papers = await finder.fetch_and_process_papers(since_days=1)
        
        print(f"\n📊 RESULTS:")
        print(f"   Total papers found: {len(papers)}")
        
        # Analyze by source
        sources = {}
        for paper in papers:
            # Try to identify source
            source = 'Unknown'
            paper_dict = str(paper.__dict__).lower()
            
            if 'biorxiv' in paper_dict or hasattr(paper, 'journal') and 'biorxiv' in str(paper.journal).lower():
                source = 'bioRxiv'
            elif hasattr(paper, 'database'):
                source = paper.database
            elif hasattr(paper, 'journal'):
                journal = str(paper.journal).lower()
                if any(term in journal for term in ['pubmed', 'pmc', 'nature', 'science', 'cell']):
                    source = 'PubMed'
                else:
                    source = f'Journal: {paper.journal}'
            else:
                source = 'PubMed/Other'
            
            sources[source] = sources.get(source, 0) + 1
        
        print(f"\n📚 Papers by source:")
        for source, count in sources.items():
            print(f"   {source}: {count} papers")
        
        # Show bioRxiv specific analysis
        biorxiv_papers = [p for p in papers if 'biorxiv' in str(p.__dict__).lower()]
        
        print(f"\n🧬 bioRxiv Analysis:")
        print(f"   bioRxiv papers found: {len(biorxiv_papers)}")
        
        if len(biorxiv_papers) == 0:
            print(f"   ⚠️ NO bioRxiv papers found!")
            print(f"   🔍 Possible reasons:")
            print(f"      - Query too specific for bioRxiv content")
            print(f"      - Date range too narrow (only 1 day)")
            print(f"      - bioRxiv API issues")
            print(f"      - Terms not matching bioRxiv paper titles/abstracts")
        else:
            print(f"   ✅ bioRxiv papers found:")
            for i, paper in enumerate(biorxiv_papers[:3]):
                title = getattr(paper, 'title', 'No title')
                print(f"      {i+1}. {title[:80]}...")
        
        # Show sample papers
        print(f"\n📄 Sample papers found:")
        for i, paper in enumerate(papers[:5]):
            title = getattr(paper, 'title', 'No title')
            journal = getattr(paper, 'journal', 'Unknown')
            print(f"   {i+1}. {title[:80]}... [{journal}]")
        
        if len(papers) > 5:
            print(f"   ... and {len(papers) - 5} more")
            
        # Test with broader search
        print(f"\n🔍 TESTING BROADER bioRxiv SEARCH:")
        config_broad = config.copy()
        config_broad['query_biorxiv'] = "[machine learning] OR [deep learning] OR [AI]"
        config_broad['databases'] = ['biorxiv']
        config_broad['limit'] = 20
        
        finder_broad = PapersFinder(config_broad)
        broad_papers = await finder_broad.fetch_and_process_papers(since_days=7)  # 7 days
        
        print(f"   Broader search (7 days, ML/AI): {len(broad_papers)} papers")
        
        if broad_papers:
            print(f"   ✅ bioRxiv IS working, issue is likely:")
            print(f"      - Query terms too specific")
            print(f"      - Date range too narrow")
        else:
            print(f"   ❌ No papers even with broad search - bioRxiv API issue")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_marrpeng_queries())
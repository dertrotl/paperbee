#!/usr/bin/env python3
"""
Detailed LLM Filtering Test Script
Zeigt genau, welche Papers gefunden, gefiltert und warum akzeptiert/abgelehnt wurden
"""

import asyncio
import yaml
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PaperBee.papers.papers_finder import PapersFinder
from PaperBee.papers.llm_filtering import LLMFilter

class DetailedLLMTest:
    def __init__(self, config_file):
        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize components
        self.finder = PapersFinder(self.config)
        self.llm_filter = None  # Will initialize when needed
        
        # Results tracking
        self.papers_found = []
        self.papers_filtered = []
        self.filter_decisions = []
    
    async def run_detailed_test(self, since_days=1):
        print("🧪 DETAILED LLM FILTERING TEST")
        print("=" * 60)
        
        # Step 1: Find papers
        print(f"\n📅 Searching papers from last {since_days} days...")
        
        try:
            # Get papers using the same method as PaperBee
            papers = await self.finder.fetch_and_process_papers(since_days)
            self.papers_found = papers
            
            print(f"📊 FOUND: {len(papers)} papers total")
            
            # Show found papers by source
            sources = {}
            for paper in papers:
                source = getattr(paper, 'journal', 'Unknown')
                if 'biorxiv' in source.lower() or 'biorxiv' in str(paper.__dict__).lower():
                    source = 'bioRxiv'
                elif hasattr(paper, 'database'):
                    source = paper.database
                else:
                    source = 'PubMed/Other'
                
                sources[source] = sources.get(source, 0) + 1
            
            print("\n📚 Papers by source:")
            for source, count in sources.items():
                print(f"   {source}: {count} papers")
            
            # Step 2: Show sample papers before filtering
            print(f"\n📄 SAMPLE PAPERS FOUND:")
            for i, paper in enumerate(papers[:5]):
                title = getattr(paper, 'title', 'No title')[:80]
                journal = getattr(paper, 'journal', 'Unknown journal')
                print(f"   {i+1}. {title}... [{journal}]")
            
            if len(papers) > 5:
                print(f"   ... and {len(papers) - 5} more")
                
        except Exception as e:
            print(f"❌ Error finding papers: {e}")
            return
        
        # Step 3: Test LLM Filtering if enabled
        if not self.llm_filter:
            print("\n⚠️ LLM Filtering disabled, stopping here.")
            return
            
        print(f"\n🤖 TESTING LLM FILTERING...")
        print(f"   Model: {self.config.get('LANGUAGE_MODEL', 'Unknown')}")
        print(f"   Provider: {self.config.get('LLM_PROVIDER', 'Unknown')}")
        print(f"   Prompt: {self.config.get('FILTERING_PROMPT', 'No prompt')[:100]}...")
        
        # Filter each paper and track decisions
        filtered_papers = []
        
        for i, paper in enumerate(papers):
            try:
                print(f"\n📋 Paper {i+1}/{len(papers)}: {getattr(paper, 'title', 'No title')[:60]}...")
                
                # Extract keywords (like PaperBee does)
                title = getattr(paper, 'title', '')
                abstract = getattr(paper, 'abstract', '')
                
                # Get LLM decision
                is_relevant = await self.test_single_paper_filter(paper, title, abstract)
                
                decision_info = {
                    'paper': paper,
                    'title': title[:100],
                    'decision': is_relevant,
                    'keywords': self.extract_sample_keywords(title, abstract)
                }
                self.filter_decisions.append(decision_info)
                
                if is_relevant:
                    filtered_papers.append(paper)
                    print(f"   ✅ ACCEPTED")
                else:
                    print(f"   ❌ REJECTED")
                
                # Add small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"   💥 ERROR filtering paper: {e}")
                continue
        
        self.papers_filtered = filtered_papers
        
        # Step 4: Summary
        print(f"\n🎯 FILTERING SUMMARY:")
        print(f"   📥 Papers found: {len(self.papers_found)}")
        print(f"   ✅ Papers accepted: {len(self.papers_filtered)}")
        print(f"   ❌ Papers rejected: {len(self.papers_found) - len(self.papers_filtered)}")
        print(f"   📊 Acceptance rate: {len(self.papers_filtered)/len(self.papers_found)*100:.1f}%")
        
        # Step 5: Show accepted papers
        if self.papers_filtered:
            print(f"\n✅ ACCEPTED PAPERS:")
            for i, paper in enumerate(self.papers_filtered):
                title = getattr(paper, 'title', 'No title')
                journal = getattr(paper, 'journal', 'Unknown')
                print(f"   {i+1}. {title[:80]}... [{journal}]")
        
        # Step 6: Show rejected samples
        rejected = [d for d in self.filter_decisions if not d['decision']]
        if rejected:
            print(f"\n❌ SAMPLE REJECTED PAPERS:")
            for i, decision in enumerate(rejected[:3]):
                print(f"   {i+1}. {decision['title']}...")
                print(f"      Keywords: {', '.join(decision['keywords'][:5])}")
        
        # Step 7: bioRxiv specific analysis
        biorxiv_found = [p for p in self.papers_found if 'biorxiv' in str(p.__dict__).lower()]
        biorxiv_accepted = [p for p in self.papers_filtered if 'biorxiv' in str(p.__dict__).lower()]
        
        print(f"\n🧬 bioRxiv ANALYSIS:")
        print(f"   📥 bioRxiv papers found: {len(biorxiv_found)}")
        print(f"   ✅ bioRxiv papers accepted: {len(biorxiv_accepted)}")
        
        if len(biorxiv_found) == 0:
            print(f"   ⚠️ NO bioRxiv papers found - this might be the main issue!")
            print(f"   🔍 Check bioRxiv query and date parameters")
    
    async def test_single_paper_filter(self, paper, title, abstract):
        """Test filtering for a single paper"""
        try:
            # Simple simulation - check if title contains relevant terms
            relevant_terms = [
                'computational', 'pathology', 'microscopy', 'segmentation', 
                'machine learning', 'deep learning', 'image', 'computer vision',
                'immunotherapy', 'cancer', 'checkpoint', 'biomarker'
            ]
            
            text = (title + " " + abstract).lower()
            relevance_score = sum(1 for term in relevant_terms if term in text)
            
            # Simulate LLM decision based on relevance
            is_relevant = relevance_score >= 2  # At least 2 relevant terms
            
            # Show decision reasoning
            found_terms = [term for term in relevant_terms if term in text]
            print(f"      Terms found: {', '.join(found_terms[:5])}")
            print(f"      Relevance score: {relevance_score}")
            
            return is_relevant
        except Exception as e:
            print(f"   💥 Filtering error: {e}")
            return False
    
    def extract_sample_keywords(self, title, abstract):
        """Extract sample keywords for display"""
        text = (title + " " + abstract).lower()
        
        # Sample relevant keywords to look for
        keywords = []
        relevant_terms = [
            'immunotherapy', 'cancer', 'checkpoint', 'pd-1', 'pd-l1', 'ctla-4',
            'car-t', 't cell', 'antibody', 'biomarker', 'tumor', 'oncology',
            'single-cell', 'scrna-seq', 'computational biology', 'organoid',
            'deep learning', 'machine learning', 'pathology', 'segmentation'
        ]
        
        for term in relevant_terms:
            if term in text:
                keywords.append(term)
        
        return keywords[:10]  # Limit to first 10

async def main():
    if len(sys.argv) < 2:
        print("Usage: python detailed_llm_test.py <config_file> [since_days]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    since_days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    if not os.path.exists(config_file):
        print(f"❌ Config file not found: {config_file}")
        sys.exit(1)
    
    tester = DetailedLLMTest(config_file)
    await tester.run_detailed_test(since_days)

if __name__ == "__main__":
    asyncio.run(main())
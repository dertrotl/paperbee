#!/usr/bin/env python3
"""
Direkter PapersFinder Test - umgeht das Posting-System
"""

import sys
import os
sys.path.insert(0, '/Users/benjamin.weinert/git_repos/paperbee/src')

from PaperBee.papers.papers_finder import PapersFinder

def main():
    print("🔍 Direct PapersFinder Test")
    print("=" * 50)
    
    try:
        # Simple test configuration
        finder = PapersFinder(
            root_dir=".",
            spreadsheet_id="dummy_id",
            google_credentials_json="dummy_creds.json",
            sheet_name="dummy_sheet",
            query_pubmed_arxiv="biomarkers hematology",
            query_biorxiv="biomarkers hematology",
            databases=["pubmed"],
            since=1,
            llm_filtering=False,
            interactive=False
        )
        
        print("📋 Configuration:")
        print(f"   🔍 PubMed Query: {finder.query_pub_arx}")
        print(f"   🧬 BioRxiv Query: {finder.query_biorxiv}")
        print(f"   🗃️ Databases: {finder.databases}")
        print(f"   📊 Limit: {finder.limit}")
        print(f"   🤖 LLM Filtering: {finder.llm_filtering}")
        print("")
        
        print("🚀 Starting paper search...")
        articles_df = finder.find_and_process_papers()
        
        print(f"\n📈 Results:")
        print(f"   📄 Total articles found: {len(articles_df)}")
        
        if len(articles_df) > 0:
            print(f"   📝 Sample titles:")
            for i, title in enumerate(articles_df['Title'].head(3)):
                print(f"      {i+1}. {title[:80]}{'...' if len(title) > 80 else ''}")
            
            print(f"\n🗂️ Article columns: {list(articles_df.columns)}")
            print(f"📊 Article sources: {articles_df['Source'].value_counts().to_dict()}")
        else:
            print("   ⚠️ No articles found!")
            
    except Exception as e:
        print(f"💥 Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

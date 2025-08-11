#!/usr/bin/env python3
"""
Debug PaperBee Pipeline - lokaler Test für Clinic Research
"""

import os
import yaml
import subprocess
import sys

def main():
    print("🔍 PaperBee Debug Test - Clinic Research")
    print("=" * 60)
    
    # Simplified config for debugging
    config = {
        "GOOGLE_SPREADSHEET_ID": "dummy_id",
        "GOOGLE_CREDENTIALS_JSON": "dummy_creds.json",
        "LOCAL_ROOT_DIR": ".",
        "databases": ["pubmed"],  # Start with just PubMed
        
        # Both queries required
        "query_biorxiv": "biomarkers hematology blood disorders",
        "query_pubmed_arxiv": "biomarkers AND (hematology OR blood disorders)",
        
        "limit": 50,  # Smaller limit for testing
        "limit_per_database": 25,
        
        # Disable LLM for initial debugging
        "LLM_FILTERING": False,
        
        "SLACK": {"is_posting_on": False},
        "TELEGRAM": {"is_posting_on": False},
        "ZULIP": {"is_posting_on": False}
    }
    
    # Save test config
    with open("debug_config.yml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print("📋 Debug Configuration:")
    print(f"   🗃️ Databases: {config['databases']}")
    print(f"   🔍 Query: {config['query_pubmed_arxiv']}")
    print(f"   📊 Limit: {config['limit']}")
    print(f"   🤖 LLM Filtering: {config['LLM_FILTERING']}")
    print("")
    
    # Run PaperBee
    try:
        print("🚀 Starting PaperBee debug run...")
        
        result = subprocess.run([
            "paperbee", "post", 
            "--config", "debug_config.yml", 
            "--since", "1"
        ], capture_output=True, text=True, timeout=180)  # 3 min timeout
        
        print("📤 Debug Output:")
        print("=" * 40)
        print(result.stdout)
        if result.stderr:
            print("⚠️ Stderr:")
            print(result.stderr)
        print("=" * 40)
        
        if result.returncode == 0:
            print("✅ Debug run completed successfully")
        else:
            print(f"❌ Debug run failed with return code {result.returncode}")
            
    except subprocess.TimeoutExpired:
        print("⏰ Debug run timed out after 3 minutes")
    except Exception as e:
        print(f"💥 Debug run error: {str(e)}")
    
    # Clean up
    try:
        os.remove("debug_config.yml")
    except:
        pass

if __name__ == "__main__":
    main()

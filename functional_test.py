#!/usr/bin/env python3
"""
Funktionaler Test für PaperBee - basiert auf den Working Workflow Configs
"""

import os
import yaml
import subprocess
import sys

def create_simple_test_config():
    """Erstelle eine minimal funktionierende Konfiguration"""
    config = {
        "GOOGLE_SPREADSHEET_ID": "test_id",
        "GOOGLE_CREDENTIALS_JSON": "./test_creds.json",
        "NCBI_API_KEY": "dummy_key",  # Required by validation
        "LOCAL_ROOT_DIR": ".",
        "databases": ["pubmed"],
        
        # Einfache, funktionierende Queries (wie in den Workflows)
        "query_biorxiv": "hematology",
        "query_pubmed_arxiv": "hematology",
        
        # Kleinere Limits für Testing
        "limit": 50,
        "limit_per_database": 25,
        
        # LLM Filtering DEAKTIVIERT für ersten Test
        "LLM_FILTERING": False,
        
        # Alle Posting-Services deaktiviert
        "SLACK": {"is_posting_on": False},
        "TELEGRAM": {"is_posting_on": False},
        "ZULIP": {"is_posting_on": False}
    }
    return config

def create_gemini_test_config():
    """Erstelle Konfiguration mit Gemini LLM-Test"""
    config = create_simple_test_config()
    config.update({
        # LLM aktivieren
        "LLM_FILTERING": True,
        "LLM_PROVIDER": "openai",
        "LANGUAGE_MODEL": "gemini-2.5-flash-lite",
        "OPENAI_API_KEY": "test_key",  # Dummy key für Test
        "OPENAI_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "FILTERING_PROMPT": "Is this paper relevant to hematology research? Answer yes or no."
    })
    return config

def run_test(config_name, config_data, test_description):
    """Führe einen einzelnen Test aus"""
    print(f"\n🧪 {test_description}")
    print("=" * 60)
    
    # Erstelle Test-Credentials
    with open("test_creds.json", "w") as f:
        f.write('{"type": "service_account", "client_email": "test@test.com"}')
    
    # Speichere Konfiguration
    config_file = f"{config_name}.yml"
    with open(config_file, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)
    
    print(f"📋 Konfiguration '{config_name}':")
    print(f"   🗃️ Databases: {config_data['databases']}")
    print(f"   🔍 PubMed Query: {config_data['query_pubmed_arxiv']}")
    print(f"   📊 Limit: {config_data['limit']}")
    print(f"   🤖 LLM Filtering: {config_data['LLM_FILTERING']}")
    if config_data['LLM_FILTERING']:
        print(f"   🎯 LLM Model: {config_data.get('LANGUAGE_MODEL', 'N/A')}")
    print("")
    
    try:
        print("🚀 Starte PaperBee...")
        result = subprocess.run([
            "/Users/benjamin.weinert/git_repos/paperbee/temp_venv/bin/paperbee", "post", 
            "--config", config_file, 
            "--since", "1"
        ], capture_output=True, text=True, timeout=120, cwd="/Users/benjamin.weinert/git_repos/paperbee")
        
        print("📤 Output:")
        print("-" * 40)
        # Erste 30 Zeilen der Stdout
        stdout_lines = result.stdout.split('\n')[:30]
        print('\n'.join(stdout_lines))
        if len(result.stdout.split('\n')) > 30:
            print("... (ausgabe gekürzt)")
        
        if result.stderr:
            print("\n⚠️ Stderr (erste 20 Zeilen):")
            stderr_lines = result.stderr.split('\n')[:20]
            print('\n'.join(stderr_lines))
        print("-" * 40)
        
        # Analysiere das Ergebnis
        success_indicators = [
            "articles from PubMed",
            "Found", 
            "papers selected",
            "completed successfully"
        ]
        
        error_indicators = [
            "404", "429", "Error", "Failed",
            "Traceback", "Exception"
        ]
        
        has_success = any(indicator in result.stdout for indicator in success_indicators)
        has_error = any(indicator in result.stdout + result.stderr for indicator in error_indicators)
        
        if result.returncode == 0 and has_success:
            print(f"✅ Test '{config_name}' erfolgreich!")
            return True
        elif has_error:
            print(f"❌ Test '{config_name}' fehlgeschlagen - Fehler erkannt")
            return False
        else:
            print(f"⚠️ Test '{config_name}' unklares Ergebnis (Code: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Test '{config_name}' Timeout nach 2 Minuten")
        return False
    except Exception as e:
        print(f"💥 Test '{config_name}' Fehler: {str(e)}")
        return False
    finally:
        # Cleanup
        for f in [config_file, "test_creds.json"]:
            try:
                os.remove(f)
            except:
                pass

def main():
    print("🔬 PaperBee Functionality Test Suite")
    print("=" * 60)
    
    # Wechsle ins PaperBee Verzeichnis und aktiviere venv
    os.chdir("/Users/benjamin.weinert/git_repos/paperbee")
    
    # Aktiviere virtual environment
    venv_python = "/Users/benjamin.weinert/git_repos/paperbee/temp_venv/bin/python"
    venv_paperbee = "/Users/benjamin.weinert/git_repos/paperbee/temp_venv/bin/paperbee"
    
    # Prüfe ob venv funktioniert
    try:
        result = subprocess.run([venv_paperbee, "--help"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("❌ Virtual Environment oder PaperBee nicht verfügbar")
            return
    except:
        print("❌ Kann PaperBee nicht ausführen")
        return
    
    print("✅ Virtual Environment und PaperBee verfügbar")
    
    tests = [
        ("basic_test", create_simple_test_config(), "Basis-Test (ohne LLM)"),
        ("gemini_test", create_gemini_test_config(), "Gemini LLM-Test")
    ]
    
    results = []
    for test_name, config, description in tests:
        success = run_test(test_name, config, description)
        results.append((test_name, success))
    
    print(f"\n📊 Test Results:")
    print("=" * 30)
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    overall_success = all(success for _, success in results)
    print(f"\nGesamtergebnis: {'✅ ALLE TESTS BESTANDEN' if overall_success else '❌ EINIGE TESTS FEHLGESCHLAGEN'}")

if __name__ == "__main__":
    main()

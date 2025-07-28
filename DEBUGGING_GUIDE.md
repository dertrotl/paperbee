# PaperBee Debugging Guide

## Problem: Keine bioRxiv Papers werden gefunden

### Ursache
Das Problem lag in der `find_and_process_papers()` Methode. Wenn separate Queries verwendet werden (`query_biorxiv` und `query_pubmed_arxiv`), wurde versucht, die bioRxiv-Datei zu laden, auch wenn keine bioRxiv-Suche durchgeführt wurde.

### Lösung
Die Logik wurde geändert, um bioRxiv-Ergebnisse nur dann zu laden, wenn bioRxiv auch tatsächlich durchsucht wurde. Siehe die Änderungen in `papers_finder.py` Zeilen 165-178.

## Problem: Mehr Keywords führen zu weniger Ergebnissen

### Ursachen
1. **AND-Verknüpfung in Queries**: Komplexe Queries mit AND-Operatoren führen zu restriktiveren Suchergebnissen
2. **LLM-Filterung**: Das LLM filtert basierend auf Titel + Keywords. Mehr Keywords können zu strengerer Filterung führen

### Debugging-Tipps

#### 1. Query-Struktur überprüfen
- **bioRxiv**: Nur OR-Verknüpfungen erlaubt, keine AND-Operatoren
- **PubMed/ArXiv**: AND, OR, AND NOT erlaubt

#### 2. Debug-Ausgaben aktivieren
Die geänderte Version zeigt jetzt:
```
Found X articles from PubMed/ArXiv
Found Y articles from bioRxiv
Found Z articles total
```

#### 3. LLM-Filterung debuggen
- Überprüfen Sie die `FILTERING_PROMPT` in Ihrer config.yml
- Zu spezifische Prompts können zu viele relevante Papers herausfiltern
- Keywords werden an das LLM weitergegeben - mehr Keywords können zu strengerer Bewertung führen

#### 4. Query-Beispiele

**Für bioRxiv (nur OR erlaubt):**
```yaml
query_biorxiv: "[single cell] OR [cell trajectory] OR [machine learning] OR [deep learning]"
```

**Für PubMed/ArXiv (komplexere Queries erlaubt):**
```yaml
query_pubmed_arxiv: "([single-cell transcriptomics]) AND ([Cell Dynamics] OR [trajectory inference]) AND ([AI] OR [machine learning] OR [deep learning]) AND NOT ([proteomics])"
```

#### 5. Testmodus verwenden
Führen Sie PaperBee mit `--interactive` Flag aus, um manuell zu sehen, welche Papers gefunden und gefiltert werden:

```bash
paperbee post --config /path/to/config.yml --interactive --since 10
```

## Zusätzliche Debugging-Schritte

1. **Logs überprüfen**: Schauen Sie sich die JSON-Dateien im `LOCAL_ROOT_DIR` an
2. **Einzelne Datenbanken testen**: 
   ```bash
   paperbee post --config config.yml --databases pubmed
   paperbee post --config config.yml --databases biorxiv
   ```
3. **LLM-Filterung deaktivieren**: Setzen Sie `LLM_FILTERING: false` um zu sehen, ob das Problem beim LLM liegt

## Konfiguration-Empfehlungen

1. **Einfache Queries verwenden**: Beginnen Sie mit simplen OR-verknüpften Keywords
2. **Schrittweise komplexer werden**: Fügen Sie AND/NOT-Operatoren nur wenn nötig hinzu
3. **LLM-Prompt testen**: Verwenden Sie `--interactive` um zu sehen, wie das LLM filtert
4. **Separate bioRxiv Query**: Verwenden Sie separate `query_biorxiv` und `query_pubmed_arxiv` für optimale Ergebnisse

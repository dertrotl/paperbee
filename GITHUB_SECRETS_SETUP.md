# GitHub Secrets Setup für PaperBee Workflows (Updated)

## ✅ **Vereinfachte Konfiguration**

Die Workflows wurden vereinfacht - **Queries und LLM-Prompts sind jetzt direkt im Workflow definiert** und müssen nicht mehr als Secrets angelegt werden.

## Erforderliche Secrets (reduziert)

### Basis-Konfiguration:
- `GOOGLE_SPREADSHEET_ID` / `GOOGLE_SPREADSHEET_ID_2`
- `GOOGLE_CREDENTIALS_JSON`
- `NCBI_API_KEY`
- `GEMINI_API_KEY`

### Slack-Integration:
- `SLACK_BOT_TOKEN` / `SLACK_BOT_TOKEN_2`
- `SLACK_CHANNEL_ID` / `SLACK_CHANNEL_ID_2`
- `SLACK_APP_TOKEN` / `SLACK_APP_TOKEN_2`

## ❌ **Nicht mehr benötigte Secrets**

Diese Secrets können Sie **löschen**, da sie jetzt direkt im Workflow definiert sind:
- ~~`FILTERING_PROMPT` / `FILTERING_PROMPT_2`~~
- ~~`RESEARCH_QUERY_BIORXIV`~~
- ~~`RESEARCH_QUERY_PUBMED_ARXIV`~~
- ~~`RESEARCH_QUERY_2`~~

## 🎯 **Workflow-spezifische Queries**

### `daily-papers-simple.yml` - Single-Cell & IBD Research:
```
[single-cell RNA sequencing] OR [spatial transcriptomics] OR [single-cell analysis] OR [scRNA-seq] OR [single cell atlas] OR [single-cell integration] OR [IBD] OR [inflammatory bowel disease] OR [Crohn disease] OR [ulcerative colitis] OR [mucosal immunology] OR [intestinal inflammation]
```

### `daily_paper_marr.yml` - Machine Learning & Computational Biology:
```
[machine learning] OR [artificial intelligence] OR [deep learning] OR [neural networks] OR [computational biology] OR [bioinformatics] OR [data science] OR [algorithm development] OR [segmentation] OR [3D segmentation] OR [vision language model] OR [computer vision] OR [image analysis] OR [medical imaging] OR [microscopy image analysis]
```

## 🔧 **Anpassung der Queries**

Um die Suchbegriffe zu ändern, bearbeiten Sie direkt die entsprechende `.yml`-Datei:

1. **Navigieren Sie zu**: `.github/workflows/`
2. **Öffnen Sie**: `daily-papers-simple.yml` oder `daily_paper_marr.yml`
3. **Suchen Sie**: `research_query = "[...]"`
4. **Ändern Sie**: Die Keywords nach Ihren Bedürfnissen
5. **Committen Sie**: Die Änderungen

## ✅ **Vorteile der neuen Konfiguration**

1. **Einheitliche Queries**: Alle Datenbanken (PubMed, ArXiv, bioRxiv) verwenden dieselben Suchbegriffe
2. **Keine Secrets für Queries**: Einfachere Verwaltung, alles im Code sichtbar
3. **Versionskontrolle**: Query-Änderungen sind in Git nachverfolgbar
4. **Transparenz**: Jeder kann sehen, welche Begriffe gesucht werden
5. **Weniger Geheimnisse**: Nur noch authentifizierungs-relevante Secrets

## 🐛 **Debugging-Features**

Die Workflows zeigen jetzt:
```
Generated config:
Query: [your query terms here]
Using same query for all databases (PubMed, ArXiv, bioRxiv)
Found X articles from PubMed/ArXiv
Found Y articles from bioRxiv
```

## 🚀 **Migration von bestehender Konfiguration**

Wenn Sie bereits Query-Secrets haben:

1. **Kopieren Sie** den Inhalt Ihrer bestehenden Secrets
2. **Bearbeiten Sie** die entsprechende `.yml`-Datei
3. **Ersetzen Sie** die `research_query` Variable
4. **Löschen Sie** die alten Secrets (optional)
5. **Testen Sie** den Workflow

## 🎯 **Query-Optimierungstipps**

### Für alle Datenbanken geeignete Queries:
- **Nur OR-Verknüpfungen verwenden**: `[term1] OR [term2] OR [term3]`
- **Spezifische Begriffe**: `[single-cell RNA-seq]` statt nur `[RNA-seq]`
- **Synonyme hinzufügen**: `[scRNA-seq] OR [single-cell transcriptomics]`
- **Keine AND/NOT-Operatoren**: Diese funktionieren nicht optimal mit bioRxiv

### LLM-Prompt Anpassung:
Die LLM-Prompts sind jetzt detaillierter und fachspezifischer:
- **Kontext geben**: Was interessiert das Labor?
- **Beispiele nennen**: Relevante Forschungsbereiche auflisten
- **Klare Anweisung**: "Answer 'yes' or 'no'" beibehalten

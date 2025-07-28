# Query-Optimierung für PaperBee

## 🐛 Problem: Zu wenige oder keine Suchergebnisse

### Häufige Ursachen:
1. **Zu spezifische Begriffe**: `[clonal hematopoiesis]` vs. `[hematopoiesis]`
2. **Zu viele seltene Begriffe**: `[NLRP3]`, `[PMVK]` sind sehr spezifisch
3. **Zu kurzer Suchzeitraum**: Nur 1-2 Tage
4. **Datenbank-spezifische Indexierung**: Nicht alle Begriffe sind überall verfügbar

## ✅ Lösungsansätze:

### 1. **Allgemeinere Begriffe verwenden**
```yaml
# Schlecht (zu spezifisch):
[clonal hematopoiesis] OR [computational hematopathology] OR [NLRP3]

# Besser (allgemeiner):
[hematopoiesis] OR [computational pathology] OR [inflammasome]
```

### 2. **Core-Begriffe identifizieren**
**Für Hämatologie-Labor (MarrPeng):**
- `[hematopoiesis]` statt `[clonal hematopoiesis]`
- `[machine learning]` statt `[machine learning pathology]`
- `[segmentation]` statt `[3D segmentation]`

**Für Single-Cell-Labor (Clinic):**
- `[single-cell]` statt `[single-cell RNA sequencing]`
- `[IBD]` statt `[VEO-IBD]`
- `[inflammation]` statt `[intestinal inflammation]`

### 3. **Suchergebnisse schrittweise verfeinern**
1. **Start breit**: `[machine learning] OR [computational biology]`
2. **LLM filtert**: Spezifische Relevanz durch detaillierten Prompt
3. **Ergebnis**: Relevante Papers aus breiter Suche

### 4. **Suchzeitraum erweitern**
```bash
# Mehr Tage für Tests:
paperbee post --config config.yml --since 7

# Für Montag (Wochenende abdecken):
since_days=3
```

## 🔧 **Aktuelle Optimierungen:**

### MarrPeng Query (vereinfacht):
```yaml
[hematopoiesis] OR [hematology] OR [computational pathology] OR [cell segmentation] OR [machine learning] OR [deep learning] OR [computer vision] OR [single cell] OR [multi-omics] OR [foundation models] OR [image analysis] OR [microscopy] OR [biomedical image analysis]
```

### Clinic Query (vereinfacht):
```yaml
[single-cell] OR [spatial transcriptomics] OR [multiomics] OR [proteomics] OR [IBD] OR [inflammatory bowel disease] OR [organoids] OR [computational biology] OR [inflammasome] OR [cytokine] OR [immune system] OR [inflammation]
```

## 🎯 **LLM-Filterung als Hauptfilter**

Die neue Strategie:
1. **Breite Suche**: Allgemeine, häufige Begriffe
2. **Präzise Filterung**: Detaillierter LLM-Prompt filtert Relevanz
3. **Bessere Abdeckung**: Mehr potentielle Papers, aber hochspezifische Filterung

## 📊 **Erwartete Verbesserungen:**

### Vor der Optimierung:
- Sehr spezifische Queries
- 0-5 Papers gefunden
- Crash bei leeren Ergebnissen

### Nach der Optimierung:
- Allgemeinere Queries
- 10-50 Papers gefunden
- LLM filtert auf 5-15 relevante Papers
- Keine Crashes bei leeren Ergebnissen

## 🧪 **Test-Empfehlungen:**

1. **Manueller Test mit erweiterten Zeitraum:**
   ```bash
   paperbee post --config config.yml --since 14 --interactive
   ```

2. **Schrittweise Query-Erweiterung:**
   - Start mit 3-5 Core-Begriffen
   - Beobachten der Ergebnisanzahl
   - Graduell weitere Begriffe hinzufügen

3. **LLM-Prompt Feintuning:**
   - Sehr spezifischen Prompt beibehalten
   - Beispiele für relevante/irrelevante Papers hinzufügen

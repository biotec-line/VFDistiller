# Screenshots Checkliste - VFDistiller (Windows Store)

Stand: 2026-03-14
Store-ID: 9MWRG32ZLDRM
Aktuelle Situation: **3 Screenshots vorhanden** (Ziel: min. 4 pro Geräteklasse)

---

## Anforderungen (Windows Store)

| Anforderung         | Wert                              |
|---------------------|-----------------------------------|
| Formate             | PNG oder JPG                      |
| Mindestanzahl       | 1 Screenshot pro Geräteklasse     |
| Empfohlen           | 4+ Screenshots pro Geräteklasse   |
| Seitenverhältnis    | 16:9 (bevorzugt)                  |
| Mindestauflösung    | 1366 x 768 px                     |
| Empfohlene Auflösung| 1920 x 1080 px                    |
| Max. Dateigröße     | 50 MB pro Screenshot              |

---

## Geräteklasse: Desktop (PC / Laptop) ← Primärziel

### Vorhandene Screenshots
*(Kein `store_assets/` oder `screenshots/` Ordner gefunden – Screenshots müssen noch angelegt werden)*

Bitte prüfe: `README/screenshots/` – dort wurde `main_view.png` eingebettet (Commit 663c376).

| # | Dateiname              | Auflösung   | Status       |
|---|------------------------|-------------|--------------|
| 1 | main_view.png          | ?           | ✅ Vorhanden |
| 2 | (unbekannt)            | ?           | ✅ Vorhanden |
| 3 | (unbekannt)            | ?           | ✅ Vorhanden |
| 4 | **FEHLT**              | 1920x1080   | ❌ Fehlt     |

### Fehlende Screenshots (Desktop)

| # | Szene                              | Empfohlene Auflösung | Priorität |
|---|------------------------------------|----------------------|-----------|
| 4 | Varianten-Tabelle mit Ergebnissen  | 1920 × 1080 px       | HOCH      |

---

## Geräteklasse: Surface Hub / Großbildschirm (optional)

| # | Szene                    | Auflösung    | Status   |
|---|--------------------------|--------------|----------|
| 1 | Hauptansicht             | 1920 × 1080  | ❌ Fehlt |
| 2 | Import-Dialog            | 1920 × 1080  | ❌ Fehlt |
| 3 | Ergebnis-Export          | 1920 × 1080  | ❌ Fehlt |
| 4 | Einstellungen            | 1920 × 1080  | ❌ Fehlt |

---

## Empfohlene Screenshot-Szenen (Content)

Folgende Szenen sollten für alle fehlenden Screenshots aufgenommen werden:

1. **Hauptansicht / Dashboard**
   - VCF-/VCF-Dateien geladen, Varianten-Tabelle gefüllt
   - Sprache: Englisch (Store-Zielgruppe international)

2. **Import-Workflow**
   - Dateiauswahl-Dialog geöffnet, eine VCF-Datei ausgewählt

3. **Analyse-Ergebnis**
   - Tabelle mit annotierten Varianten, gnomAD-AF-Werte sichtbar

4. **Export / Bericht**
   - PDF-Export-Dialog oder fertiger PDF-Report

5. **Einstellungen / Ressourcen-Setup**
   - Referenzgenome auswählen, Download-Fortschritt

6. **Sprach-Umschaltung DE/EN**
   - Menü "Optionen → Sprache" sichtbar

---

## Aufnahme-Hinweise

- Fenster auf **1920 × 1080** skalieren (oder Snipping Tool mit fester Größe)
- Windows-Taskleiste ausblenden oder Vollbild-Screenshot
- Beispieldaten verwenden (keine echten Patientendaten!)
- Store-Sprache der UI: **Englisch** (internationale Nutzer)
- Dateiname-Konvention: `screenshot_desktop_<szene>_1920x1080.png`

---

## To-Do Zusammenfassung

- [ ] `store_assets/` Ordner anlegen
- [ ] Screenshot 4 (Desktop): Varianten-Tabelle mit Ergebnissen (1920×1080)
- [ ] Optional: Screenshots für Surface Hub (4 Stück, 1920×1080)
- [ ] Alle Screenshots in `store_assets/desktop/` ablegen
- [ ] Store-Submission mit 4+ Desktop-Screenshots aktualisieren

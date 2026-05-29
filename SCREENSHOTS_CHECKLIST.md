# Screenshots Checkliste - VFDistiller

Stand: 2026-03-14
Früheres Store-Listing: 9MWRG32ZLDRM (seit 2026-04-12 zurückgezogen)
Aktuelle Situation: **2 README-Screenshots vorhanden**; GitHub ist der aktive
Vertriebskanal, Store-Screenshots sind nur noch historisch relevant.

---

## Anforderungen (historisch: Windows Store)

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

Aktiv für GitHub eingebunden: `README/screenshots/`.

| # | Dateiname              | Auflösung   | Status       |
|---|------------------------|-------------|--------------|
| 1 | `README/screenshots/main_view.png` | 1920×1080 | ✅ In README eingebunden |
| 2 | `README/screenshots/main.png` | 1397×1025 | ✅ In README eingebunden |

### Fehlende Screenshots (Desktop)

| # | Szene                              | Empfohlene Auflösung | Priorität |
|---|------------------------------------|----------------------|-----------|
| 3 | Varianten-Tabelle mit Beispieldaten | 1920 × 1080 px       | Mittel |
| 4 | Export-Dialog oder fertiger PDF-Bericht | 1920 × 1080 px       | Mittel |

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

- [x] Vorhandene GitHub-Screenshots in README/README.de sichtbar einbinden
- [ ] Optional: Beispieldaten-Screenshot der gefüllten Varianten-Tabelle erzeugen
- [ ] Optional: Export-Screenshot mit synthetischen Daten erzeugen
- [ ] Keine Store-Submission aktualisieren, solange die GitHub-only-Entscheidung gilt

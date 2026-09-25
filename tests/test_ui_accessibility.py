"""Automated accessibility, keyboard navigation and UX contract tests for VFDistiller.

Standards: WCAG 2.1 AA / BITV 2.0
Covers:
  - Global application keyboard shortcuts (Ctrl+O, Ctrl+R, Ctrl+Return, Ctrl+E, Ctrl+Shift+E, Ctrl+P, F5, F1, Escape).
  - Main variant table keyboard interaction (Return, Space, Ctrl+C, Ctrl+A, Escape).
  - Clipboard TSV formatting and selection copy.
  - Dialog keyboard ergonomics and Escape/Return modality (Settings, Quality, ResourceSetup, Shortcuts).
  - Accessible tooltips attached to interactive controls.
  - Tier-2 6-language translation parity and German umlaut integrity for all UX/A11y strings.
  - Isolated live GUI subprocess verification.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from translator import SUPPORTED_LANGUAGES

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_PATH = ROOT_DIR / "Variant_Fusion_pro_V17.py"
TRANSLATIONS_FILE = ROOT_DIR / "locales" / "translations.json"


def test_main_window_keyboard_shortcuts_contract():
    """Verify that all WCAG AA required global shortcuts are bound on the main window."""
    src = SRC_PATH.read_text(encoding="utf-8")

    # File open
    assert 'self.bind("<Control-o>", lambda _e: self.choose_file())' in src
    assert 'self.bind("<Control-O>", lambda _e: self.choose_file())' in src

    # Pipeline start
    assert 'self.bind("<Control-r>", lambda _e: self.on_start())' in src
    assert 'self.bind("<Control-R>", lambda _e: self.on_start())' in src
    assert 'self.bind("<Control-Return>", lambda _e: self.on_start())' in src

    # Export shortcuts
    assert 'self.bind("<Control-e>", lambda _e: self.export_csv())' in src
    assert 'self.bind("<Control-E>", lambda _e: self.export_csv())' in src
    assert 'self.bind("<Control-Shift-E>", lambda _e: self.export_excel())' in src
    assert 'self.bind("<Control-Shift-e>", lambda _e: self.export_excel())' in src
    assert 'self.bind("<Control-p>", lambda _e: self.export_pdf())' in src
    assert 'self.bind("<Control-P>", lambda _e: self.export_pdf())' in src

    # Refresh & Help
    assert 'self.bind("<F5>", lambda _e: self.on_refresh())' in src
    assert 'self.bind("<F1>", lambda _e: self.show_shortcuts_dialog())' in src

    # Escape cancellation
    assert 'self.bind("<Escape>", self._handle_escape)' in src


def test_treeview_keyboard_navigation_and_shortcuts_contract():
    """Verify that the variants treeview exposes required keyboard navigation and shortcuts."""
    src = SRC_PATH.read_text(encoding="utf-8")

    # Enter / Return / Space row activation
    assert 'self.tree.bind("<Return>", self._on_tree_return)' in src
    assert 'self.tree.bind("<KP_Enter>", self._on_tree_return)' in src
    assert 'self.tree.bind("<space>", self._on_tree_return)' in src

    # Clipboard copy
    assert 'self.tree.bind("<Control-c>", self._copy_selection_to_clipboard)' in src
    assert 'self.tree.bind("<Control-C>", self._copy_selection_to_clipboard)' in src

    # Select all
    assert 'self.tree.bind("<Control-a>", self._select_all_variants)' in src
    assert 'self.tree.bind("<Control-A>", self._select_all_variants)' in src

    # Deselect / Escape
    assert 'self.tree.bind("<Escape>", self._clear_table_selection)' in src


def test_table_clipboard_and_selection_methods_contract():
    """Verify that _copy_selection_to_clipboard, _select_all_variants and _clear_table_selection exist and implement TSV clipboard formatting."""
    src = SRC_PATH.read_text(encoding="utf-8")

    # _copy_selection_to_clipboard method
    assert "def _copy_selection_to_clipboard(self, event=None):" in src
    assert "self.clipboard_clear()" in src
    assert "self.clipboard_append(tsv_text)" in src
    assert 'self._t("{count} Variante(n) in Zwischenablage kopiert", count=count)' in src

    # _select_all_variants method
    assert "def _select_all_variants(self, event=None):" in src
    assert "self.tree.selection_set(children)" in src

    # _clear_table_selection method
    assert "def _clear_table_selection(self, event=None):" in src
    assert "self.tree.selection_remove(selection)" in src


def test_quality_settings_dialog_keyboard_ergonomics_contract():
    """Verify that QualitySettingsDialog binds Escape and Return and localizes UI controls."""
    src = SRC_PATH.read_text(encoding="utf-8")

    assert 'self.bind("<Escape>", lambda _e: self.on_cancel())' in src
    assert 'self.bind("<Control-Return>", lambda _e: self.on_apply())' in src
    assert 'self.bind("<Return>", lambda _e: self.on_apply())' in src
    assert 'text=self._t("Abbrechen")' in src
    assert 'text=self._t("Einstellungen Übernehmen")' in src


def test_resource_setup_dialog_keyboard_ergonomics_contract():
    """Verify that ResourceSetupDialog binds Escape and Return and localizes actions."""
    src = SRC_PATH.read_text(encoding="utf-8")

    assert 'self.win.bind("<Escape>", lambda _e: self._on_close())' in src
    assert 'self.win.bind("<Return>", lambda _e: self._on_close())' in src
    assert 'text=self._t("Diesen Dialog nicht mehr anzeigen")' in src
    assert 'text=self._t("Schließen")' in src
    assert 'text=self._t("Später")' in src


def test_open_general_settings_keyboard_ergonomics_contract():
    """Verify that open_general_settings binds Escape and Control-Return and localizes tabs and buttons."""
    src = SRC_PATH.read_text(encoding="utf-8")

    assert 'settings_window.title(self._t("Allgemeine Einstellungen & Links"))' in src
    assert 'settings_window.bind("<Escape>", lambda _e: settings_window.destroy())' in src
    assert 'settings_window.bind("<Control-Return>", lambda _e: save_all())' in src
    assert 'notebook.add(tab_general, text=self._t("Allgemein"))' in src
    assert 'notebook.add(tab_resources, text=self._t("Ressourcen"))' in src
    assert 'notebook.add(tab_links, text=self._t("Spalten-Links"))' in src
    assert 'notebook.add(tab_api, text=self._t("APIs & Services"))' in src
    assert 'text=self._t("Speichern & Schließen")' in src
    assert 'text=self._t("Auf Standard zurücksetzen")' in src


def test_shortcuts_dialog_content_contract():
    """Verify that show_shortcuts_dialog populates all shortcuts and references accessibility standards."""
    src = SRC_PATH.read_text(encoding="utf-8")

    assert 'def show_shortcuts_dialog(self):' in src
    assert 'dlg.title(self._t("Tastaturkürzel & Barrierefreiheit"))' in src
    assert 'dlg.bind("<Escape>", lambda _e: dlg.destroy())' in src
    assert 'BITV 2.0 / WCAG 2.1 AA' in src

    # Verify documented shortcuts in list
    assert '("Strg+O / Ctrl+O", self._t("Eingabedatei auswählen"))' in src
    assert '("Strg+R / Ctrl+Return", self._t("Analyse der ausgewählten Datei starten"))' in src
    assert '("Escape", self._t("Laufende Analyse stoppen"))' in src
    assert '("F5", self._t("Ergebnisse neu laden"))' in src
    assert '(self._t("Strg+E / Ctrl+E"), self._t("Tabelle als CSV-Datei exportieren"))' in src
    assert '(self._t("Strg+Umschalt+E"), self._t("Tabelle als Excel-Arbeitsmappe exportieren"))' in src
    assert '(self._t("Strg+P / Ctrl+P"), self._t("Ergebnisse als PDF-Bericht exportieren"))' in src
    assert '(self._t("Strg+C / Ctrl+C (Tabelle)"), self._t("Ausgewählte Varianten in Zwischenablage kopieren"))' in src
    assert '(self._t("Strg+A / Ctrl+A (Tabelle)"), self._t("Alle Varianten in Tabelle auswählen"))' in src
    assert '(self._t("Escape (Tabelle)"), self._t("Auswahl in Tabelle aufheben"))' in src
    assert '(self._t("Eingabe / Leertaste (Tabelle)"), self._t("Primären Link der ausgewählten Variante öffnen"))' in src
    assert '("F1", self._t("Dieses Hilfefenster anzeigen"))' in src


def test_interactive_controls_have_tooltips_contract():
    """Verify that tooltips are properly attached to key interactive and export controls."""
    src = SRC_PATH.read_text(encoding="utf-8")

    # Table & Log tooltips
    assert 'self._attach_tooltip(\n            self.tree,\n            self._t("Tabelle: Pfeiltasten navigieren, Return/Leertaste öffnet primären Link, Strg+C kopiert Auswahl, Strg+A wählt alle aus, Escape hebt Markierung auf.")\n        )' in src or 'self._attach_tooltip(\r\n            self.tree,\r\n            self._t("Tabelle: Pfeiltasten navigieren, Return/Leertaste öffnet primären Link, Strg+C kopiert Auswahl, Strg+A wählt alle aus, Escape hebt Markierung auf.")\r\n        )' in src
    assert 'self._attach_tooltip(self.log_text, self._t("Systemprotokoll: Zeigt Echtzeit-Meldungen des Analyse- und Filterprozesses."))' in src

    # VCF export radiobuttons
    assert 'rb_complete = ttk.Radiobutton(exp_frame, text=self._t("Original (+Anno)"), variable=self.vcf_export_mode, value="complete")' in src
    assert 'self._attach_tooltip(rb_complete, self._t("Exportiert alle Varianten mit Annotationen im Original-VCF-Format"))' in src
    assert 'rb_filtered = ttk.Radiobutton(exp_frame, text=self._t("Gefiltert (Sichtbar)"), variable=self.vcf_export_mode, value="filtered")' in src
    assert 'self._attach_tooltip(rb_filtered, self._t("Exportiert nur die aktuell sichtbaren und gefilterten Varianten"))' in src

    # Export buttons tooltips
    assert 'self._attach_tooltip(csv_btn, self._t("Tabelle als CSV-Datei exportieren"))' in src
    assert 'self._attach_tooltip(excel_btn, self._t("Tabelle als Excel-Arbeitsmappe exportieren"))' in src
    assert 'self._attach_tooltip(pdf_btn, self._t("Ergebnisse als PDF-Bericht exportieren"))' in src
    assert 'self._attach_tooltip(vcf_btn, self._t("Varianten als VCF-Datei exportieren"))' in src


def test_a11y_translations_parity_and_umlaut_hygiene():
    """Verify 100% 6-language parity for UX/A11y strings and authentic German umlauts."""
    with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    a11y_keys = [
        "Allgemeine Einstellungen & Links",
        "Tabelle als CSV-Datei exportieren (Strg+E)",
        "Tabelle als Excel-Arbeitsmappe exportieren (Strg+Umschalt+E)",
        "Ergebnisse als PDF-Bericht exportieren (Strg+P)",
        "Tabelle: Pfeiltasten navigieren, Return/Leertaste öffnet primären Link, Strg+C kopiert Auswahl, Strg+A wählt alle aus, Escape hebt Markierung auf.",
        "Systemprotokoll: Zeigt Echtzeit-Meldungen des Analyse- und Filterprozesses.",
        "Ausgewählte Varianten in Zwischenablage kopiert",
        "{count} Variante(n) in Zwischenablage kopiert",
        "Alle Varianten in Tabelle auswählen",
        "Auswahl in Tabelle aufheben",
        "Varianten ausgewählt",
        "Strg+E / Ctrl+E",
        "Strg+Umschalt+E",
        "Strg+P / Ctrl+P",
        "Strg+C / Ctrl+C (Tabelle)",
        "Strg+A / Ctrl+A (Tabelle)",
        "Escape (Tabelle)",
        "Eingabe / Leertaste (Tabelle)",
        "Vordefinierte Profile",
        "Quality-Gates",
        "Vorschau",
        "Original (+Anno)",
        "Exportiert alle Varianten mit Annotationen im Original-VCF-Format",
        "Exportiert nur die aktuell sichtbaren und gefilterten Varianten",
    ]

    for key in a11y_keys:
        assert key in catalog, f"Key '{key}' missing from translations catalog"
        entry = catalog[key]
        for lang in SUPPORTED_LANGUAGES:
            val = entry.get(lang)
            assert val and str(val).strip(), f"Key '{key}' has empty translation for '{lang}'"

    # German umlauts check on keys that specifically contain umlauts
    umlauts = ("\u00e4", "\u00f6", "\u00fc", "\u00c4", "\u00d6", "\u00dc", "\u00df")
    de_samples = [
        catalog["Tabelle: Pfeiltasten navigieren, Return/Leertaste öffnet primären Link, Strg+C kopiert Auswahl, Strg+A wählt alle aus, Escape hebt Markierung auf."]["de"],
        catalog["Ausgewählte Varianten in Zwischenablage kopiert"]["de"],
        catalog["Alle Varianten in Tabelle auswählen"]["de"],
        catalog["Varianten ausgewählt"]["de"],
        catalog["Speichern & Schließen"]["de"],
        catalog["Auf Standard zurücksetzen"]["de"],
    ]
    for text in de_samples:
        assert any(u in text for u in umlauts), f"Expected German umlauts in text: {text}"


def test_live_gui_isolated_smoke():
    """Verify live App creation and keybindings in an isolated Python process."""
    smoke_script = """
import sys
sys.path.insert(0, ".")
from Variant_Fusion_pro_V17 import App

app = App()
app.withdraw()

# Verify live bindings
app_b = app.bind()
assert "<Key-Escape>" in app_b
assert "<Key-F1>" in app_b
assert "<Control-Key-Return>" in app_b

tree_b = app.tree.bind()
assert "<Key-space>" in tree_b
assert "<Key-Return>" in tree_b
assert "<Control-Key-c>" in tree_b or "<Control-Key-C>" in tree_b
assert "<Control-Key-a>" in tree_b or "<Control-Key-A>" in tree_b

app.destroy()
"""
    result = subprocess.run(
        [sys.executable, "-c", smoke_script],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"Live GUI smoke failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

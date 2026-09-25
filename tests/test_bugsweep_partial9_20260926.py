# -*- coding: utf-8 -*-
"""
Bug-Sweep Block 9 (2026-09-26) — Spalten-Index-Synchronisation & TSV-Export-Härtung
===================================================================================

Bereich: Tabellen-Interaktion, Spalten-Sichtbarkeit, TSV-Clipboard-Export und
Genom-Link-Aktivierung in _copy_selection_to_clipboard, _on_tree_return und _generic_click_handler

Behobene Bugs:
1. _copy_selection_to_clipboard: `row_vals` iterierte naiv über `range(len(visible_cols))`
   und griff mit `values[i]` auf den Zeilen-Tupel zu. Da `values` in `tree.item(row_id)`
   strikt der vollständigen `self.columns`-Reihenfolge entspricht, wurden bei
   ausgeblendeten Spalten (`visible_columns != self.columns`) die Werte der ersten N
   Spalten von `self.columns` extrahiert. Dadurch kam es zu einem systematischen
   Spalten-Shift (z. B. `ref`/`alt` unter `rsid`/`genotype`), was beim Einfügen in
   Excel/Bioinformatik-Tools fehlerhafte Tabellen erzeugte.
   Fix: Zuordnung über `col_to_val = {col: values[idx] for idx, col in enumerate(self.columns) if idx < len(values)}`
   und Extraktion für `col in visible_cols`.
2. _on_tree_return: Iterierte über `enumerate(visible_cols)` und wies `row_data[vc] = values[i]`
   zu. Dadurch wurden die Feldwerte in `row_data` bei ausgeblendeten Spalten verschoben;
   beim Öffnen primärer Links (z. B. dbSNP für rsID) wurde das falsche Allel/Feld als
   Suchparameter übergeben.
   Fix: Vollständiges `row_data = {col: col_to_val.get(col, "") for col in self.columns}`.
3. _generic_click_handler: Bildete `row_data` ebenfalls über `enumerate(visible_cols)`
   und `values[i]`, wodurch Template-Parameter `{chr}`, `{pos}`, `{gene}`, `{consequence}`
   in `DEFAULT_COLUMN_LINKS` (z. B. gnomAD oder PubMed) mit verschobenen Spaltenwerten
   formatiert wurden.
   Fix: Vollständiges `row_data = {col: col_to_val.get(col, "") for col in self.columns}`
   sowie defensiver Null-Guard für `hasattr(self, "db") and self.db`.
4. Fehlende TSV-Sanitisierung: Eingebettete Tabulatoren oder Zeilenumbrüche in
   Tabellenzellen wurden bisher unmaskiert in die Zwischenablage geschrieben, was
   beim Einfügen die Spalten- und Zeilengrenzen zerriss.
   Fix: `.replace("\\t", " ").replace("\\r\\n", " ").replace("\\n", " ")`.
"""
import ast
import pathlib
from unittest.mock import MagicMock

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
SRC_FILE = ROOT_DIR / "Variant_Fusion_pro_V17.py"
SRC = SRC_FILE.read_text(encoding="utf-8")

# Extract and compile target methods hermetically from AST
_tree = ast.parse(SRC)
_app_node = None
for _node in _tree.body:
    if isinstance(_node, ast.ClassDef) and _node.name == "App":
        _app_node = _node
        break

_NS = {
    "COLUMN_LABELS": {
        "chr": "chr", "pos": "pos", "ref": "ref", "alt": "alt", "build": "build",
        "rsid": "rsid", "genotype": "genotype", "af": "AF", "cadd": "CADD", "gene": "Gene",
        "consequence": "Consequence", "phenotypes": "Phenotypes", "pubmed": "PubMed"
    }
}

for _node in _app_node.body:
    if isinstance(_node, ast.FunctionDef) and _node.name in (
        "_copy_selection_to_clipboard", "_on_tree_return", "_generic_click_handler"
    ):
        _code_segment = ast.get_source_segment(SRC, _node)
        exec(_code_segment, _NS)

_copy_selection_to_clipboard = _NS["_copy_selection_to_clipboard"]
_on_tree_return = _NS["_on_tree_return"]
_generic_click_handler = _NS["_generic_click_handler"]


# ---------------------------------------------------------------------------
# Statische Quelltext-Prüfungen
# ---------------------------------------------------------------------------

def test_no_naive_displaycols_range_in_clipboard_copy():
    """Verify that _copy_selection_to_clipboard does not naively index values[i] by range(len(visible_cols))."""
    assert "row_vals = [str(values[i]) if i < len(values) else \"\" for i in range(len(visible_cols))]" not in SRC
    assert "col_to_val = {col: values[idx] for idx, col in enumerate(self.columns) if idx < len(values)}" in SRC


def test_no_displaycols_enumeration_in_tree_return():
    """Verify that _on_tree_return uses column-to-value mapping instead of enumerate(visible_cols)."""
    assert "for i, vc in enumerate(visible_cols):\n            if i < len(values):\n                row_data[vc] = values[i]" not in SRC


def test_tsv_sanitization_in_clipboard_copy():
    """Verify that tabs and newlines are sanitized in clipboard TSV values."""
    assert '.replace("\\t", " ").replace("\\r\\n", " ").replace("\\n", " ")' in SRC


# ---------------------------------------------------------------------------
# Funktionale Verhaltensprüfungen
# ---------------------------------------------------------------------------

def test_clipboard_copy_with_hidden_columns_maintains_alignment():
    """Verify that hiding columns does not shift values across headers when copying to clipboard."""
    app = MagicMock()
    app.columns = ["chr", "pos", "ref", "alt", "build", "rsid", "genotype", "af", "cadd", "gene"]
    app.visible_columns = {"chr", "pos", "rsid", "gene"}  # ref, alt, build, genotype, af, cadd are hidden
    app._current_displaycolumns = lambda: [c for c in app.columns if c in app.visible_columns]
    app._t = lambda text, **kwargs: text.format(**kwargs) if kwargs else text
    app.logger = MagicMock()

    # Simulated row in treeview item: values has all columns in app.columns order
    sample_values = ("chr1", "1000", "A", "G", "GRCh38", "rs12345", "0/1", "0.01", "25.0", "BRCA1")
    app.tree = MagicMock()
    app.tree.selection.return_value = ["row_1"]
    app.tree.item.return_value = {"values": sample_values}

    copied_payload = []
    app.clipboard_clear = MagicMock()
    app.clipboard_append = lambda text: copied_payload.append(text)
    app.update = MagicMock()

    ret = _copy_selection_to_clipboard(app)
    assert ret == "break"
    assert len(copied_payload) == 1

    lines = copied_payload[0].split("\n")
    assert len(lines) == 2

    headers = lines[0].split("\t")
    row_vals = lines[1].split("\t")

    assert headers == ["chr", "pos", "rsid", "Gene"]
    # Critical assertion: rsid and gene must NOT be shifted to 'A' and 'G' (ref and alt)
    assert row_vals[0] == "chr1"
    assert row_vals[1] == "1000"
    assert row_vals[2] == "rs12345"  # NOT "A"
    assert row_vals[3] == "BRCA1"    # NOT "G"


def test_clipboard_copy_sanitizes_newlines_and_tabs():
    """Verify that embedded tabs or newlines inside variant values do not corrupt TSV structure."""
    app = MagicMock()
    app.columns = ["chr", "pos", "consequence", "phenotypes"]
    app.visible_columns = {"chr", "pos", "consequence", "phenotypes"}
    app._current_displaycolumns = lambda: [c for c in app.columns if c in app.visible_columns]
    app._t = lambda text, **kwargs: text.format(**kwargs) if kwargs else text
    app.logger = MagicMock()

    sample_values = ("chr7", "117199646", "missense_variant\textra_note", "Cystic fibrosis\r\nsevere")
    app.tree = MagicMock()
    app.tree.selection.return_value = ["row_1"]
    app.tree.item.return_value = {"values": sample_values}

    copied_payload = []
    app.clipboard_clear = MagicMock()
    app.clipboard_append = lambda text: copied_payload.append(text)
    app.update = MagicMock()

    _copy_selection_to_clipboard(app)
    lines = copied_payload[0].split("\n")
    assert len(lines) == 2  # exactly header + 1 row, no broken extra lines

    row_vals = lines[1].split("\t")
    assert len(row_vals) == 4  # exactly 4 tab-delimited columns
    assert row_vals[2] == "missense_variant extra_note"
    assert row_vals[3] == "Cystic fibrosis severe"


def test_on_tree_return_with_hidden_columns_resolves_correct_rsid():
    """Verify that keyboard Return row activation resolves the actual rsid and gene, even when preceding columns are hidden."""
    app = MagicMock()
    app.columns = ["chr", "pos", "ref", "alt", "build", "rsid", "genotype", "gene"]
    app.visible_columns = {"chr", "pos", "rsid", "gene"}  # ref, alt, build hidden
    app._current_displaycolumns = lambda: [c for c in app.columns if c in app.visible_columns]
    app.column_links = {
        "rsid": {"trigger": "single", "template": "https://www.ncbi.nlm.nih.gov/snp/{rsid}"}
    }
    app.db = MagicMock()
    app._handle_column_click = MagicMock()

    sample_values = ("chr2", "2000", "T", "C", "GRCh37", "rs9999", "1/1", "MTHFR")
    app.tree = MagicMock()
    app.tree.selection.return_value = ["row_1"]
    app.tree.item.return_value = {"values": sample_values}

    _on_tree_return(app)

    # _handle_column_click must be called for "rsid" with row_data containing "rs9999", NOT "T"
    assert app._handle_column_click.call_count == 1
    call_args = app._handle_column_click.call_args[0]
    assert call_args[0] == "rsid"
    assert call_args[1] == "single"
    passed_row_data = call_args[2]
    assert passed_row_data["rsid"] == "rs9999"
    assert passed_row_data["gene"] == "MTHFR"
    assert passed_row_data["ref"] == "T"
    assert passed_row_data["alt"] == "C"


def test_generic_click_handler_with_hidden_columns_passes_uncontaminated_row_data():
    """Verify that cell click handler passes accurate row_data when some columns are hidden."""
    app = MagicMock()
    app.columns = ["chr", "pos", "ref", "alt", "build", "gene", "pubmed"]
    # Hide ref and alt: visible_cols = ["chr", "pos", "build", "gene", "pubmed"]
    app.visible_columns = {"chr", "pos", "build", "gene", "pubmed"}
    app._current_displaycolumns = lambda: [c for c in app.columns if c in app.visible_columns]
    app._handle_column_click = MagicMock()
    app.db = None

    # Treeview coordinates point to column #4 (which is 'gene' in visible_cols: chr=0, pos=1, build=2, gene=3 -> col_id="#4")
    app.tree = MagicMock()
    app.tree.identify.return_value = "cell"
    app.tree.identify_column.return_value = "#4"
    app.tree.identify_row.return_value = "row_1"
    sample_values = ("chr17", "43044295", "G", "A", "GRCh38", "BRCA1", "PubMed")
    app.tree.item.return_value = {"values": sample_values}

    mock_event = MagicMock()
    mock_event.x = 200
    mock_event.y = 50

    _generic_click_handler(app, mock_event, "single")

    assert app._handle_column_click.call_count == 1
    call_args = app._handle_column_click.call_args[0]
    col_name = call_args[0]
    passed_row_data = call_args[2]

    assert col_name == "gene"
    assert passed_row_data["gene"] == "BRCA1"  # NOT "A" or "GRCh38"
    assert passed_row_data["chr"] == "chr17"
    assert passed_row_data["pos"] == "43044295"
    assert passed_row_data["build"] == "GRCh38"

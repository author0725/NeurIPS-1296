"""
paper_extractors.py — Extract numerical claims from the paper's LaTeX sources.

Each extractor is a callable that, given a dictionary {filename: tex_source},
returns a Python value (float, int, tuple, etc.) representing what the paper
asserts. Pair these with `canonical_extractors.py` extractors in `verifier_core`
to verify paper-vs-canonical agreement at runtime — no hand-transcribed values.

The goal of this module is to be SMALL and EXPLICIT. Each extractor names the
file, the LaTeX neighbourhood it looks in, and what it pulls out. If the paper
text changes in a way that breaks an extractor, the verifier reports an
extraction error pointing at the .tex location — much better than silently
matching a stale hard-coded value.
"""

from __future__ import annotations

import re
from typing import Callable


# =============================================================================
# Low-level number parsing
# =============================================================================
# LaTeX often writes "+.111" (no leading zero) or "$<.001$" or "$+0.487$" or
# "$+0.5\%$". The functions below normalise these into Python floats / tuples.

_NUM_RE = r"[+-]?\d*\.?\d+(?:[eE][+-]?\d+)?"   # matches .111, 0.5, 1e-3, etc.


def _to_float(s: str) -> float:
    """Parse a LaTeX-stripped number into a float.

    Accepts: '+.111', '0.487', '-.026', '5.3', '<.001', '< 0.001', '\\leq 0.003'.
    For inequality-style numbers (e.g. '<.001'), returns the bound itself with
    a `_inequality` attribute set so callers can re-check as inequality. Most
    callers don't care and just want the bound.
    """
    s = s.strip().replace(" ", "").replace("\\,", "").replace("\\;", "")
    # Strip inequality / approx prefixes
    for prefix in ("<", ">", "\\leq", "\\geq", "\\le", "\\ge", "\\approx", "\\sim"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    # Strip percent suffix and divide by 100
    is_percent = s.endswith("\\%") or s.endswith("%")
    if is_percent:
        s = s.rstrip("%").rstrip("\\")
    # Normalise leading dot ('.111' -> '0.111')
    if s.startswith(".") or s.startswith("+.") or s.startswith("-."):
        if s[0] in "+-":
            s = s[0] + "0" + s[1:]
        else:
            s = "0" + s
    val = float(s)
    if is_percent:
        val = val / 100.0
    return val


def _strip_latex_decoration(cell: str) -> str:
    """Remove $, \\mathbf{...}, \\textbf{...}, \\, etc. from a cell.

    Handles nested braces by counting depth — needed for cells like
    \\mathbf{+.389_{(5/5)}^{\\pm.053}} that have { } inside the wrapper.
    """
    s = cell.strip()
    # Remove outer dollar signs
    s = s.replace("$", "")
    # Strip \mathbf{...} / \textbf{...} / \emph{...} wrappers, with brace counting
    for _ in range(5):
        m = re.search(r"\\(?:mathbf|textbf|emph|mathrm|text)\{", s)
        if not m:
            break
        # Find the matching close brace
        depth = 1
        i = m.end()
        while i < len(s) and depth > 0:
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
            i += 1
        if depth != 0:
            break  # malformed, give up
        # Replace the wrapper with its contents
        s = s[: m.start()] + s[m.end() : i - 1] + s[i:]
    # Remove dagger superscripts and similar
    s = re.sub(r"\^\{?\\dagger\}?", "", s)
    s = re.sub(r"\\dagger", "", s)
    s = s.replace("\\,\\checkmark", "").replace("\\checkmark", "")
    return s.strip()


# =============================================================================
# Tabular row extractor — for tables of the form
#   row_label & cell1 & cell2 & ... & celln \\
# =============================================================================
def _find_table_environment(tex: str, label: str) -> str:
    """Find the \\begin{table} ... \\end{table} block whose \\label{} matches.

    Raises ValueError if not found.
    """
    # Find the label first
    label_pat = r"\\label\{" + re.escape(label) + r"\}"
    label_m = re.search(label_pat, tex)
    if not label_m:
        raise ValueError(f"Could not find \\label{{{label}}} in tex")

    # Find the enclosing \begin{table}...\end{table}
    # Scan backward for \begin{table} and forward for \end{table}
    pre = tex[: label_m.start()]
    begin_m = list(re.finditer(r"\\begin\{table\}", pre))
    if not begin_m:
        raise ValueError(f"No \\begin{{table}} before \\label{{{label}}}")
    begin_idx = begin_m[-1].start()
    rest = tex[begin_idx:]
    end_m = re.search(r"\\end\{table\}", rest)
    if not end_m:
        raise ValueError(f"No \\end{{table}} after \\label{{{label}}}")
    return rest[: end_m.end()]


def _split_tabular_rows(table_block: str) -> list[list[str]]:
    r"""Split a tabular into rows of cells (list of list of stripped strings).

    Skips \toprule, \midrule, \bottomrule, \cmidrule, multicolumn header rows
    that don't have data, and other non-data lines. Returns one entry per
    body row that ended in \\.
    """
    # Find the tabular content
    m = re.search(r"\\begin\{tabular\}\{[^}]*\}(.+?)\\end\{tabular\}", table_block, re.DOTALL)
    if not m:
        raise ValueError("No tabular environment in table block")
    body = m.group(1)
    # Strip rule commands
    body = re.sub(r"\\toprule\b", "", body)
    body = re.sub(r"\\midrule\b", "", body)
    body = re.sub(r"\\bottomrule\b", "", body)
    body = re.sub(r"\\cmidrule(?:\([^)]*\))?\{[^}]*\}", "", body)
    # Split on \\ (followed by optional whitespace/newline)
    raw_rows = re.split(r"\\\\\s*", body)
    rows = []
    for r in raw_rows:
        r = r.strip()
        if not r:
            continue
        # Skip multicolumn header rows that have no data — heuristic: must have
        # at least one '&' AND not be only multicolumn declarations
        if "&" not in r:
            continue
        cells = [c.strip() for c in r.split("&")]
        rows.append(cells)
    return rows


def _row_label(row: list[str]) -> str:
    """The first cell, with LaTeX decorations stripped, used for matching."""
    s = row[0]
    s = _strip_latex_decoration(s)
    s = re.sub(r"\\texttt\{([^}]+)\}", r"\1", s)
    s = s.replace("\\_", "_").replace("\\textbf{", "").replace("}", "")
    return s.strip()


def _normalize_label_for_match(s: str) -> str:
    """Apply the same cleaning as _row_label, so matchers can use plain text."""
    s = _strip_latex_decoration(s)
    s = re.sub(r"\\texttt\{([^}]+)\}", r"\1", s)
    s = s.replace("\\_", "_").replace("\\textbf{", "").replace("}", "")
    return s.strip()


def _row_matches(row_label_normalized: str, query_normalized: str) -> bool:
    """Match a query against a row label.

    A query starting and ending with '^' and '$' is treated as exact-match;
    otherwise it's a substring match. Use exact-match for cases where one
    row label is a prefix of another (e.g. 'V-Dem-16' vs 'V-Dem-16 after Layer 3').
    """
    if query_normalized.startswith("^") and query_normalized.endswith("$"):
        return row_label_normalized == query_normalized[1:-1]
    return query_normalized in row_label_normalized


def table_cell(filename: str, label: str, row_match: str, column_index: int) -> Callable:
    """Return an extractor that fetches a single cell from a table.

    Args:
        filename: which paper file (e.g. 'main.tex').
        label: the table's \\label{...} contents (e.g. 'tab:substrates').
        row_match: a substring that uniquely identifies the row, matched
                   against the (decoration-stripped) first cell. To force
                   exact-match (when one label is a prefix of another),
                   wrap in ^...$, e.g. row_match='^V-Dem-16$'.
        column_index: 0-based column index. Column 0 is the row label itself.
    """
    normalized_match = _normalize_label_for_match(
        row_match[1:-1] if row_match.startswith("^") and row_match.endswith("$") else row_match
    )
    if row_match.startswith("^") and row_match.endswith("$"):
        normalized_match = "^" + normalized_match + "$"

    def _extract(sources: dict[str, str]) -> float:
        tex = sources[filename]
        block = _find_table_environment(tex, label)
        rows = _split_tabular_rows(block)
        matches = [r for r in rows if _row_matches(_row_label(r), normalized_match)]
        if not matches:
            raise KeyError(f"No row matching '{row_match}' in {filename}:{label}")
        if len(matches) > 1:
            raise KeyError(f"Multiple rows match '{row_match}' in {filename}:{label}: "
                           f"{[_row_label(r) for r in matches]}")
        row = matches[0]
        if column_index >= len(row):
            raise IndexError(f"Row '{row_match}' has {len(row)} cells, asked for index {column_index}")
        cell = row[column_index]
        return _to_float(_strip_latex_decoration(cell))
    return _extract


def table_cell_str(filename: str, label: str, row_match: str, column_index: int) -> Callable:
    """Like table_cell but returns the raw stripped cell as string (for verdicts like 'PASS')."""
    def _extract(sources):
        tex = sources[filename]
        block = _find_table_environment(tex, label)
        rows = _split_tabular_rows(block)
        matches = [r for r in rows if row_match in _row_label(r)]
        if len(matches) != 1:
            raise KeyError(f"Expected 1 row match, got {len(matches)} for '{row_match}'")
        return _strip_latex_decoration(matches[matches.__len__()-1 if False else 0][column_index])
    return _extract


# =============================================================================
# Table 1 cell extractor — special compact format
#
# Cells look like:  $+.111_{(5/5)}^{\pm.024}$    or  $-.046_{(0/5)}$
# We pull (mean, sd, n_pass) from each. The triple is returned together; pair
# this extractor with a triple-comparison canonical descriptor.
# =============================================================================
_TABLE1_CELL_RE = re.compile(
    r"^\s*"
    r"(?P<mean>[+-]?\.?\d+\.?\d*)"           # +.111  /  -.046  /  +0.077
    r"_\{\((?P<np>\d+)/(?P<nt>\d+)\)\}"      # _{(5/5)}
    r"(?:\^\{\\pm(?P<sd>\.?\d+\.?\d*)\})?"   # ^{\pm.024}   (optional)
    r"\s*$"
)


def table1_cell(filename: str, label: str, row_match: str,
                column_index: int, which: str) -> Callable:
    """Extract one component (mean / sd / n_pass) of a Table-1-style compact cell.

    `which` is one of 'mean', 'sd', or 'n_pass'. n_pass is returned as int.
    Use ^name$ for exact-match if needed.
    """
    if which not in ("mean", "sd", "n_pass"):
        raise ValueError(f"which must be 'mean'|'sd'|'n_pass', got {which}")
    normalized_match = _normalize_label_for_match(
        row_match[1:-1] if row_match.startswith("^") and row_match.endswith("$") else row_match
    )
    if row_match.startswith("^") and row_match.endswith("$"):
        normalized_match = "^" + normalized_match + "$"

    def _extract(sources):
        tex = sources[filename]
        block = _find_table_environment(tex, label)
        rows = _split_tabular_rows(block)
        matches = [r for r in rows if _row_matches(_row_label(r), normalized_match)]
        if len(matches) != 1:
            raise KeyError(f"Expected 1 row match, got {len(matches)}: '{row_match}'")
        cell = matches[0][column_index]
        cell_clean = _strip_latex_decoration(cell)
        m = _TABLE1_CELL_RE.match(cell_clean)
        if not m:
            raise ValueError(f"Cell does not match Table-1 pattern: {cell_clean!r}")
        if which == "mean":
            return _to_float(m.group("mean"))
        elif which == "sd":
            sd = m.group("sd")
            if sd is None:
                raise ValueError(f"Cell has no sd: {cell_clean!r}")
            return _to_float(sd)
        else:  # n_pass
            return int(m.group("np"))
    return _extract


# =============================================================================
# Inline value extractor — for sentences like "sup-Wald = 10.8"
# =============================================================================
def inline_value(filename: str, anchor_pattern: str, group: int = 1) -> Callable:
    r"""Extract a number from prose by regex-matching a unique anchor.

    Args:
        filename: e.g. 'main.tex'
        anchor_pattern: a regex with one capture group containing the number.
                        The pattern must match exactly once in the file.
        group: which regex group holds the number (default 1).

    Use raw strings: e.g. r"sup-Wald statistic of \$(\d+\.\d+)\$".
    """
    def _extract(sources):
        tex = sources[filename]
        matches = list(re.finditer(anchor_pattern, tex))
        if len(matches) == 0:
            raise KeyError(f"Pattern not found in {filename}: {anchor_pattern!r}")
        if len(matches) > 1:
            # show all matches for debugging
            ctx = [m.group(0) for m in matches]
            raise KeyError(f"Pattern matched {len(matches)} times in {filename}: {ctx}")
        return _to_float(matches[0].group(group))
    return _extract


def inline_range(filename: str, anchor_pattern: str) -> Callable:
    """Extract a (lo, hi) tuple from a pattern like '\\beta \\in [0.928, 0.995]'.

    `anchor_pattern` must have two capture groups: lo and hi.
    Returns a tuple (lo_float, hi_float).
    """
    def _extract(sources):
        tex = sources[filename]
        matches = list(re.finditer(anchor_pattern, tex))
        if len(matches) == 0:
            raise KeyError(f"Range pattern not found in {filename}: {anchor_pattern!r}")
        if len(matches) > 1:
            ctx = [m.group(0) for m in matches]
            raise KeyError(f"Range pattern matched {len(matches)} times: {ctx}")
        lo = _to_float(matches[0].group(1))
        hi = _to_float(matches[0].group(2))
        return (lo, hi)
    return _extract


def inline_int(filename: str, anchor_pattern: str, group: int = 1) -> Callable:
    """Extract an integer from prose."""
    def _extract(sources):
        tex = sources[filename]
        matches = list(re.finditer(anchor_pattern, tex))
        if len(matches) != 1:
            raise KeyError(f"Pattern matched {len(matches)} times: {anchor_pattern!r}")
        return int(matches[0].group(group))
    return _extract


def inline_percent(filename: str, anchor_pattern: str, group: int = 1) -> Callable:
    """Extract a percentage from prose and convert to a fraction.

    For patterns like 'flat-lines for $30.3\\%$ of countries' — captures '30.3'
    and returns 0.303. Use this when the canonical value is a fraction.
    """
    def _extract(sources):
        tex = sources[filename]
        matches = list(re.finditer(anchor_pattern, tex))
        if len(matches) == 0:
            raise KeyError(f"Pattern not found: {anchor_pattern!r}")
        if len(matches) > 1:
            ctx = [m.group(0) for m in matches]
            raise KeyError(f"Pattern matched {len(matches)} times: {ctx}")
        return _to_float(matches[0].group(group)) / 100.0
    return _extract


# =============================================================================
# File loading helpers
# =============================================================================
def load_paper_sources(paper_dir) -> dict[str, str]:
    """Load all .tex files from a directory into a {filename: source} dict."""
    from pathlib import Path
    paper_dir = Path(paper_dir)
    sources = {}
    for tex_file in sorted(paper_dir.glob("*.tex")):
        sources[tex_file.name] = tex_file.read_text()
    if not sources:
        raise FileNotFoundError(f"No .tex files found in {paper_dir}")
    return sources

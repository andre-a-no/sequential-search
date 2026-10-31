"""ADR-008 dependency rules, enforced mechanically (D1/D2).

These tests are the cheap version of an import-linter contract: they read the
source tree instead of importing it, so they run in any environment and catch a
violation before the code ever reaches a reviewer.
"""
from __future__ import annotations

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "src" / "sequential_search"

UPSTREAM = "sequential_analysis"
INTERPRETATION = ("sequentialist_core", "sequentialist_visuals")


def _module_upstream_refs(path: pathlib.Path) -> list[str]:
    """Return names imported from upstream by this module (top-level only)."""
    tree = ast.parse(path.read_text(), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root == UPSTREAM or root in INTERPRETATION:
                found.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root == UPSTREAM or root in INTERPRETATION:
                    found.append(alias.name)
    return found


def _literal_upstream_imports(path: pathlib.Path) -> list[int]:
    """Line numbers of `import sequential_analysis` inside function bodies.

    A lazy import is legal only at the adapter boundary; elsewhere it hides the
    optional-dependency edge and breaks D1's auditability.
    """
    hits: list[int] = []
    tree = ast.parse(path.read_text(), filename=str(path))
    scopes = [n for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mods = [node.module] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
            for m in mods:
                if m and m.split(".")[0] == UPSTREAM:
                    inside = any(
                        scope.lineno < node.lineno <= (scope.end_lineno or scope.lineno)
                        for scope in scopes
                    )
                    if inside:
                        hits.append(node.lineno)
    return hits


def test_d1_only_the_adapter_touches_upstream():
    """D1: `stats/procedure.py` is the single module allowed to know about upstream."""
    allowed = {"stats/procedure.py"}
    offenders: list[str] = []
    for path in sorted(SRC.rglob("*.py")):
        rel = str(path.relative_to(SRC))
        refs = _module_upstream_refs(path)
        # module-level lazy imports count as references too
        refs += ["(lazy)" for _ in _literal_upstream_imports(path)]
        if refs and rel not in allowed:
            offenders.append(f"{rel}: {sorted(set(refs))}")
    assert not offenders, "upstream leaked outside the adapter boundary:\n" + "\n".join(offenders)


def test_d1_lazy_import_stays_inside_the_adapter():
    """The optional-dependency import must be lazy *and* confined to the adapter."""
    proc = SRC / "stats" / "procedure.py"
    assert _literal_upstream_imports(proc), (
        "the upstream import must be lazy: `pip install sequential-search` has to work without it"
    )


def test_d2_nothing_below_is_known_here():
    """D2: the math layer never mentions the interpretation layer, even in imports."""
    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text()
        for name in INTERPRETATION:
            assert f"import {name}" not in text, f"{path}: D2 violation ({name})"


def test_graph_contracts_are_upstream_free():
    """D1 corollary: ontology and budgets must be importable with no upstream installed."""
    for path in sorted((SRC / "graph").rglob("*.py")):
        assert not _module_upstream_refs(path), f"{path.name}: graph/ must stay upstream-free"
    base = SRC / "policy" / "base.py"
    assert not _module_upstream_refs(base), "budget arithmetic must not depend on upstream"

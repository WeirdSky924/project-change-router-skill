from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from router_support.import_graph import build_import_graph, PYTHON_SUFFIXES, TYPESCRIPT_SUFFIXES


def _walk(seeds: set[str], adjacency: dict[str, set[str]]) -> list[str]:
    seen, pending = set(seeds), list(sorted(seeds))
    while pending:
        node = pending.pop()
        for target in sorted(adjacency.get(node, set())):
            if target not in seen:
                seen.add(target)
                pending.append(target)
    return sorted(seen)


def build_path_relations(repo_root: Path, route_paths: Iterable[str], source_paths: Iterable[str],
                         *, previous_edges: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    seeds = set(route_paths)
    paths = sorted(set(source_paths) | seeds)
    diagnostics = []
    files = []
    supported = PYTHON_SUFFIXES | TYPESCRIPT_SUFFIXES
    for relative in paths:
        path = repo / relative
        if Path(relative).is_absolute() or ".." in Path(relative).parts or not path.resolve().is_relative_to(repo):
            diagnostics.append({"path": relative, "code": "path_escape"})
        elif path.is_symlink():
            diagnostics.append({"path": relative, "code": "symlink_unknown"})
        elif path.suffix.lower() in supported and path.is_file():
            files.append(path)
        elif path.suffix.lower() in supported:
            diagnostics.append({"path": relative, "code": "source_missing"})
        elif path.suffix.lower() in {".java", ".sql"}:
            diagnostics.append({"path": relative, "code": "unsupported_relation_language"})
    graph = build_import_graph(repo, files)
    diagnostics.extend({"path": item.path, "code": item.code} for item in graph.diagnostics)
    edges = [{"source": e.source, "target": e.target, "kind": "runtime_import" if e.runtime else "type_import"}
             for e in graph.edges]
    forward: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    for edge in [*edges, *previous_edges]:
        forward[str(edge["source"])].add(str(edge["target"]))
        reverse[str(edge["target"])].add(str(edge["source"]))
    # Do not alternate directions through a shared dependency and pull in siblings.
    dependencies = _walk(seeds, forward)
    impacted = _walk(seeds, reverse)
    return {"complete": not diagnostics, "edges": edges, "diagnostics": diagnostics,
            "dependency_paths": dependencies, "impacted_paths": impacted,
            "closure_paths": sorted(set(dependencies) | set(impacted)),
            "mode": "directed_imports" if not diagnostics else "conservative_unknown"}

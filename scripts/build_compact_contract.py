"""Rebuild the canonical compact SchemaCrosswalk contract deterministically.

The readable policy-v6 source is the audit reference.  This generator removes
only Python trivia and alpha-renames collision-checked module-internal bindings.
It deliberately keeps annotations, runtime literals, class members, imports,
and every public contract surface unchanged.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
import copy
import hashlib
import importlib.metadata
import io
import json
import keyword
from pathlib import Path
import string
import tokenize
from typing import Any

from python_minifier import minify
from python_minifier.transforms.remove_annotations import RemoveAnnotationsOptions


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = PROJECT_ROOT / "reference" / "schema_crosswalk_policy_v6_readable.py.txt"
COMPACT_PATH = PROJECT_ROOT / "contracts" / "schema_crosswalk.py"
SOURCE_MAP_PATH = PROJECT_ROOT / "reference" / "schema_crosswalk_compact_source_map.json"

MINIFIER_VERSION = "3.2.0"
MAX_COMPACT_BYTES = 45_000
EXPECTED_REFERENCE_BYTES = 59_302
EXPECTED_REFERENCE_SHA256 = (
    "3EF88992C3E87515173B3C57987507AACA29723D44B018C135D3A669AE905124"
)
EXPECTED_COMPACT_BYTES = 43_407
EXPECTED_COMPACT_SHA256 = (
    "8383D532E3C4CC142369630DA777BC64B5DF10BC1A6640DBCA5C343674B2E7B9"
)
EXPECTED_DEPENDS_HEADER = (
    '# { "Depends": "py-genlayer:'
    '1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }'
)
EXPECTED_PYRIGHT_DIRECTIVE = (
    "# pyright: strict, reportUnknownMemberType=false, "
    "reportUnknownLambdaType=false"
)

REFLECTION_CALLS = frozenset(
    {
        "compile",
        "delattr",
        "eval",
        "exec",
        "getattr",
        "globals",
        "hasattr",
        "locals",
        "setattr",
        "vars",
    }
)
REFLECTION_ATTRIBUTES = frozenset(
    {
        "__class__",
        "__closure__",
        "__code__",
        "__dict__",
        "__func__",
        "__globals__",
        "__module__",
        "__name__",
        "__qualname__",
    }
)
REFLECTION_MODULES = frozenset({"importlib", "inspect", "marshal", "pickle"})


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _module_internal_bindings(tree: ast.Module) -> list[str]:
    bindings: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bindings.append(node.name)
            continue
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        bindings.extend(
            target.id for target in targets if isinstance(target, ast.Name)
        )

    if len(bindings) != len(set(bindings)):
        raise RuntimeError("module-internal bindings are not unique")
    if "SchemaCrosswalk" in bindings:
        raise RuntimeError("public contract class must never be alpha-renamed")
    return bindings


def reflection_hazards(tree: ast.Module, bindings: set[str]) -> list[str]:
    """Return reflection or rebinding constructs that make token renaming unsafe."""

    hazards: list[str] = []
    allowed_module_stores: set[int] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            allowed_module_stores.update(
                id(target)
                for target in node.targets
                if isinstance(target, ast.Name) and target.id in bindings
            )
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id in bindings
        ):
            allowed_module_stores.add(id(node.target))

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in REFLECTION_CALLS:
                hazards.append(f"reflection call {node.func.id} at line {node.lineno}")
        if isinstance(node, ast.Attribute):
            if node.attr in REFLECTION_ATTRIBUTES:
                hazards.append(f"reflection attribute {node.attr} at line {node.lineno}")
            if node.attr in bindings:
                hazards.append(
                    f"module binding reused as attribute {node.attr} at line {node.lineno}"
                )
        if isinstance(node, ast.keyword) and node.arg in bindings:
            hazards.append(
                f"module binding reused as keyword {node.arg} at line {node.lineno}"
            )
        if isinstance(node, ast.arg) and node.arg in bindings:
            hazards.append(
                f"module binding reused as argument {node.arg} at line {node.lineno}"
            )
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and node.id in bindings
            and id(node) not in allowed_module_stores
        ):
            hazards.append(
                f"module binding rebound in nested scope {node.id} at line {node.lineno}"
            )
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            imported_module = (
                node.module.split(".", 1)[0]
                if isinstance(node, ast.ImportFrom) and node.module
                else ""
            )
            imported_names = (
                {alias.name.split(".", 1)[0] for alias in node.names}
                if isinstance(node, ast.Import)
                else set()
            )
            if imported_module in REFLECTION_MODULES or imported_names & REFLECTION_MODULES:
                hazards.append(f"reflection module imported at line {node.lineno}")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in bindings:
                hazards.append(
                    f"module binding name embedded as runtime text at line {node.lineno}"
                )

    return sorted(set(hazards))


def _compact_syntax(readable: str) -> str:
    lines = readable.splitlines()
    if not lines or lines[0] != EXPECTED_DEPENDS_HEADER:
        raise RuntimeError("readable source has an unexpected Depends header")
    try:
        pyright_directive = next(
            line for line in lines if line.startswith("# pyright:")
        )
    except StopIteration as exc:
        raise RuntimeError("readable source is missing its Pyright directive") from exc
    if pyright_directive != EXPECTED_PYRIGHT_DIRECTIVE:
        raise RuntimeError("readable source has an unexpected Pyright directive")

    compact_body = minify(
        readable,
        remove_annotations=RemoveAnnotationsOptions(
            remove_variable_annotations=False,
            remove_return_annotations=False,
            remove_argument_annotations=False,
            remove_class_attribute_annotations=False,
        ),
        remove_pass=False,
        remove_literal_statements=False,
        combine_imports=False,
        hoist_literals=False,
        rename_locals=False,
        rename_globals=False,
        remove_object_base=False,
        convert_posargs_to_args=False,
        remove_asserts=False,
        remove_debug=False,
        remove_explicit_return_none=False,
        remove_builtin_exception_brackets=False,
        constant_folding=False,
        prefer_single_line=False,
    )
    # GenVM requires the dependency metadata line to be terminated before any
    # following metadata directive.  Preserve one blank physical line here;
    # a Pyright directive immediately on line 2 is rejected by hosted Studio.
    compact = (
        f"{EXPECTED_DEPENDS_HEADER}\n\n"
        f"{EXPECTED_PYRIGHT_DIRECTIVE}\n{compact_body}\n"
    )
    if ast.dump(ast.parse(readable), include_attributes=False) != ast.dump(
        ast.parse(compact), include_attributes=False
    ):
        raise RuntimeError("trivia removal changed the Python AST")
    return compact


def _alpha_mapping(compact_syntax: str, bindings: list[str]) -> dict[str, str]:
    used_names = {
        token.string
        for token in tokenize.generate_tokens(io.StringIO(compact_syntax).readline)
        if token.type == tokenize.NAME
    }
    candidates = [
        first + second
        for first in string.ascii_letters
        for second in string.ascii_letters
        if first + second not in used_names
        and not keyword.iskeyword(first + second)
    ]
    if len(candidates) < len(bindings):
        raise RuntimeError("not enough collision-free two-character identifiers")
    mapping = dict(zip(bindings, candidates[: len(bindings)], strict=True))
    if set(mapping.values()) & used_names:
        raise RuntimeError("alpha-renaming generated an identifier collision")
    if len(set(mapping.values())) != len(mapping):
        raise RuntimeError("alpha-renaming generated duplicate identifiers")
    return mapping


def _rename_tokens(source: str, mapping: dict[str, str]) -> str:
    renamed: list[tokenize.TokenInfo] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.NAME and token.string in mapping:
            token = tokenize.TokenInfo(
                token.type,
                mapping[token.string],
                token.start,
                token.end,
                token.line,
            )
        renamed.append(token)
    return tokenize.untokenize(renamed)


class _AlphaRenameAst(ast.NodeTransformer):
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
        node.id = self.mapping.get(node.id, node.id)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:  # noqa: N802
        node.name = self.mapping.get(node.name, node.name)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(  # noqa: N802
        self, node: ast.AsyncFunctionDef
    ) -> ast.AST:
        node.name = self.mapping.get(node.name, node.name)
        return self.generic_visit(node)


def _string_literals(tree: ast.Module) -> Counter[str]:
    return Counter(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )


def build_artifacts() -> tuple[bytes, bytes, dict[str, str]]:
    installed_version = importlib.metadata.version("python-minifier")
    if installed_version != MINIFIER_VERSION:
        raise RuntimeError(
            f"python-minifier {MINIFIER_VERSION} is required; found {installed_version}"
        )

    readable_bytes = REFERENCE_PATH.read_bytes()
    if len(readable_bytes) != EXPECTED_REFERENCE_BYTES:
        raise RuntimeError("readable reference has an unexpected byte length")
    if _sha256(readable_bytes) != EXPECTED_REFERENCE_SHA256:
        raise RuntimeError("readable reference SHA-256 does not match the audited source")
    readable = readable_bytes.decode("utf-8")
    readable_tree = ast.parse(readable)
    bindings = _module_internal_bindings(readable_tree)
    hazards = reflection_hazards(readable_tree, set(bindings))
    if hazards:
        raise RuntimeError("unsafe alpha-renaming hazards:\n" + "\n".join(hazards))

    compact_syntax = _compact_syntax(readable)
    mapping = _alpha_mapping(compact_syntax, bindings)
    compact = _rename_tokens(compact_syntax, mapping)
    compact_bytes = compact.encode("utf-8")

    compact_tree = ast.parse(compact)
    expected_tree = _AlphaRenameAst(mapping).visit(copy.deepcopy(readable_tree))
    ast.fix_missing_locations(expected_tree)
    if ast.dump(expected_tree, include_attributes=False) != ast.dump(
        compact_tree, include_attributes=False
    ):
        raise RuntimeError("compact source is not AST alpha-equivalent")
    if _string_literals(readable_tree) != _string_literals(compact_tree):
        raise RuntimeError("compact source changed runtime string literals")
    if len(compact_bytes) > MAX_COMPACT_BYTES:
        raise RuntimeError("compact source exceeds its maximum byte budget")
    if len(compact_bytes) != EXPECTED_COMPACT_BYTES:
        raise RuntimeError("compact source has an unexpected byte length")
    if _sha256(compact_bytes) != EXPECTED_COMPACT_SHA256:
        raise RuntimeError("compact source SHA-256 is not the frozen release hash")

    source_map: dict[str, Any] = {
        "compact": {
            "bytes": len(compact_bytes),
            "maxBytes": MAX_COMPACT_BYTES,
            "path": "contracts/schema_crosswalk.py",
            "sha256": _sha256(compact_bytes),
        },
        "format": "schema-crosswalk-compact-source-map/1",
        "generator": {
            "package": "python-minifier",
            "version": MINIFIER_VERSION,
        },
        "readableReference": {
            "bytes": len(readable_bytes),
            "path": "reference/schema_crosswalk_policy_v6_readable.py.txt",
            "sha256": _sha256(readable_bytes),
        },
        "renamedModuleBindings": mapping,
        "transform": {
            "alphaRename": "collision-checked module-internal bindings only",
            "preserved": [
                "all runtime string literals",
                "all type annotations",
                "class and class-member names",
                "imports",
                "public methods, arguments, decorators, and return types",
                "storage field names and annotations",
            ],
            "syntax": "AST-identical trivia removal",
        },
    }
    source_map_bytes = (
        json.dumps(source_map, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")
    return compact_bytes, source_map_bytes, mapping


def _write_if_changed(path: Path, data: bytes) -> None:
    if path.exists() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify generated files")
    mode.add_argument("--write", action="store_true", help="rewrite generated files")
    args = parser.parse_args()

    compact_bytes, source_map_bytes, mapping = build_artifacts()
    if args.write:
        _write_if_changed(COMPACT_PATH, compact_bytes)
        _write_if_changed(SOURCE_MAP_PATH, source_map_bytes)
    else:
        if not COMPACT_PATH.exists() or COMPACT_PATH.read_bytes() != compact_bytes:
            raise SystemExit("canonical compact contract is not reproducible; run --write")
        if not SOURCE_MAP_PATH.exists() or SOURCE_MAP_PATH.read_bytes() != source_map_bytes:
            raise SystemExit("compact source map is not reproducible; run --write")

    print(
        json.dumps(
            {
                "compactBytes": len(compact_bytes),
                "compactSha256": _sha256(compact_bytes),
                "mode": "write" if args.write else "check",
                "renamedModuleBindings": len(mapping),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import ast
from collections import Counter
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tokenize


ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / "reference" / "schema_crosswalk_policy_v6_readable.py.txt"
COMPACT = ROOT / "contracts" / "schema_crosswalk.py"
SOURCE_MAP = ROOT / "reference" / "schema_crosswalk_compact_source_map.json"
BUILDER = ROOT / "scripts" / "build_compact_contract.py"

REFERENCE_SHA256 = "3EF88992C3E87515173B3C57987507AACA29723D44B018C135D3A669AE905124"
COMPACT_SHA256 = "8383D532E3C4CC142369630DA777BC64B5DF10BC1A6640DBCA5C343674B2E7B9"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _sources() -> tuple[str, str]:
    return REFERENCE.read_text(encoding="utf-8"), COMPACT.read_text(encoding="utf-8")


def _source_map() -> dict[str, object]:
    return json.loads(SOURCE_MAP.read_text(encoding="utf-8"))


class _InverseAlphaRename(ast.NodeTransformer):
    def __init__(self, inverse: dict[str, str]) -> None:
        self.inverse = inverse

    def visit_Name(self, node: ast.Name) -> ast.AST:  # noqa: N802
        node.id = self.inverse.get(node.id, node.id)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:  # noqa: N802
        node.name = self.inverse.get(node.name, node.name)
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(  # noqa: N802
        self, node: ast.AsyncFunctionDef
    ) -> ast.AST:
        node.name = self.inverse.get(node.name, node.name)
        return self.generic_visit(node)


def _literal_multiset(tree: ast.Module) -> Counter[str]:
    return Counter(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )


def _decorator_name(node: ast.expr) -> str:
    return ast.unparse(node)


def _contract_surface(tree: ast.Module) -> dict[str, object]:
    contract = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SchemaCrosswalk"
    )
    storage = [
        (
            node.target.id,
            ast.dump(node.annotation, include_attributes=False),
        )
        for node in contract.body
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    ]
    methods: list[tuple[object, ...]] = []
    for node in contract.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorators = tuple(_decorator_name(item) for item in node.decorator_list)
        if not any(name in {"gl.public.view", "gl.public.write"} for name in decorators):
            continue
        arguments = tuple(
            (
                argument.arg,
                ast.dump(argument.annotation, include_attributes=False)
                if argument.annotation is not None
                else None,
            )
            for argument in node.args.args
        )
        methods.append(
            (
                node.name,
                decorators,
                arguments,
                ast.dump(node.returns, include_attributes=False)
                if node.returns is not None
                else None,
            )
        )
    return {"class": contract.name, "methods": methods, "storage": storage}


def test_readable_reference_is_the_frozen_audited_source() -> None:
    data = REFERENCE.read_bytes()
    assert len(data) == 59_302
    assert _sha256(data) == REFERENCE_SHA256


def test_compact_ast_is_readable_ast_under_inverse_alpha_mapping() -> None:
    readable, compact = _sources()
    mapping_raw = _source_map()["renamedModuleBindings"]
    assert isinstance(mapping_raw, dict)
    mapping = {str(key): str(value) for key, value in mapping_raw.items()}
    inverse = {value: key for key, value in mapping.items()}
    assert len(inverse) == len(mapping) == 68

    restored = _InverseAlphaRename(inverse).visit(copy.deepcopy(ast.parse(compact)))
    ast.fix_missing_locations(restored)
    assert ast.dump(restored, include_attributes=False) == ast.dump(
        ast.parse(readable), include_attributes=False
    )


def test_all_runtime_prompt_and_error_string_literals_are_exact() -> None:
    readable_tree = ast.parse(REFERENCE.read_text(encoding="utf-8"))
    compact_tree = ast.parse(COMPACT.read_text(encoding="utf-8"))
    readable_literals = _literal_multiset(readable_tree)
    compact_literals = _literal_multiset(compact_tree)
    assert compact_literals == readable_literals

    long_literals = [value for value in readable_literals if len(value) > 1_000]
    assert len(long_literals) == 2
    for marker in ("[INPUT]", "[NOT_FOUND]", "[LLM_ERROR]"):
        assert readable_literals[marker] == 1


def test_public_abi_and_storage_surface_are_identical() -> None:
    readable_tree = ast.parse(REFERENCE.read_text(encoding="utf-8"))
    compact_tree = ast.parse(COMPACT.read_text(encoding="utf-8"))
    mapping_raw = _source_map()["renamedModuleBindings"]
    assert isinstance(mapping_raw, dict)
    inverse = {str(value): str(key) for key, value in mapping_raw.items()}
    restored_compact_tree = _InverseAlphaRename(inverse).visit(
        copy.deepcopy(compact_tree)
    )
    ast.fix_missing_locations(restored_compact_tree)
    readable_surface = _contract_surface(readable_tree)
    compact_surface = _contract_surface(restored_compact_tree)
    assert compact_surface == readable_surface
    assert len(compact_surface["methods"]) == 13
    assert len(compact_surface["storage"]) == 3


def test_rebuild_is_deterministic_and_matches_the_frozen_compact_hash() -> None:
    spec = importlib.util.spec_from_file_location("compact_builder", BUILDER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    compact_bytes, source_map_bytes, mapping = module.build_artifacts()

    assert compact_bytes == COMPACT.read_bytes()
    assert source_map_bytes == SOURCE_MAP.read_bytes()
    assert len(compact_bytes) == 43_407
    assert len(compact_bytes) <= 45_000
    assert _sha256(compact_bytes) == COMPACT_SHA256
    assert len(mapping) == 68


def test_alpha_renaming_has_no_collisions_or_reflection_hazards() -> None:
    readable, _ = _sources()
    tree = ast.parse(readable)
    mapping_raw = _source_map()["renamedModuleBindings"]
    assert isinstance(mapping_raw, dict)
    mapping = {str(key): str(value) for key, value in mapping_raw.items()}
    aliases = set(mapping.values())
    original_names = {
        token.string
        for token in tokenize.generate_tokens(io.StringIO(readable).readline)
        if token.type == tokenize.NAME
    }
    assert len(aliases) == len(mapping)
    assert aliases.isdisjoint(original_names)

    forbidden_calls = {
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
    forbidden_attributes = {
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
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in forbidden_calls
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden_attributes
            assert node.attr not in mapping
        if isinstance(node, ast.keyword) and node.arg is not None:
            assert node.arg not in mapping
        if isinstance(node, ast.arg):
            assert node.arg not in mapping

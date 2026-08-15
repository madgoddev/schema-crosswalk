import json
import os
import tempfile


# genlayer-test 0.29.2 deletes its fd-0 backing file before fd 0 is restored.
# POSIX permits that; Windows does not. Keep this compatibility shim test-local.
if os.name == "nt":
    from gltest.direct import loader as _direct_loader
    from gltest.direct.vm import VMContext as _VMContext

    _original_cleanup = _VMContext._cleanup_after_deactivate

    def _windows_safe_inject_message(vm):
        try:
            from genlayer.py import calldata
            from genlayer.py.types import Address
        except ImportError:
            return

        sender = vm.sender
        if isinstance(sender, bytes):
            sender = Address(sender)
        contract = vm._contract_address
        if isinstance(contract, bytes):
            contract = Address(contract)
        origin = vm.origin
        if isinstance(origin, bytes):
            origin = Address(origin)

        encoded = calldata.encode(
            {
                "contract_address": contract,
                "sender_address": sender,
                "origin_address": origin,
                "stack": [],
                "value": vm._value,
                "datetime": vm._datetime,
                "is_init": False,
                "chain_id": vm._chain_id,
                "entry_kind": 0,
                "entry_data": b"",
                "entry_stage_data": None,
            }
        )
        fd, path = tempfile.mkstemp(prefix="schemacrosswalk-gltest-")
        try:
            os.write(fd, encoded)
            os.lseek(fd, 0, os.SEEK_SET)
            vm._original_stdin_fd = os.dup(0)
            os.dup2(fd, 0)
            vm._schemacrosswalk_stdin_path = path
        finally:
            os.close(fd)

    def _windows_safe_cleanup(self):
        path = getattr(self, "_schemacrosswalk_stdin_path", None)
        _original_cleanup(self)
        if path is not None:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
            self._schemacrosswalk_stdin_path = None

    _direct_loader._inject_message_to_fd0 = _windows_safe_inject_message
    _VMContext._cleanup_after_deactivate = _windows_safe_cleanup


SOURCE_SCHEMA = json.dumps(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "LegacyCustomer",
        "type": "object",
        "required": ["customer_id", "display_name", "tier"],
        "properties": {
            "customer_id": {
                "type": "integer",
                "description": "The same stable customer identifier represented by target field id; convert its base-10 integer representation to text.",
            },
            "display_name": {
                "type": "string",
                "description": "The same customer-facing name represented by target field name.",
            },
            "tier": {
                "type": "string",
                "description": "The same loyalty level represented by target field level, encoded B=bronze, S=silver, and G=gold.",
                "enum": ["B", "S", "G"],
            },
            "signed_up": {
                "type": ["string", "null"],
                "format": "date-time",
                "description": "The same account-creation instant represented by target field createdAt.",
            },
        },
    },
    separators=(",", ":"),
)


TARGET_SCHEMA = json.dumps(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "CustomerProfile",
        "type": "object",
        "required": ["id", "name", "level", "region"],
        "properties": {
            "id": {
                "type": "string",
                "description": "The same stable customer identifier represented by source field customer_id, encoded as text.",
            },
            "name": {
                "type": "string",
                "description": "The same customer-facing name represented by source field display_name.",
            },
            "level": {
                "type": "string",
                "description": "The same loyalty level represented by source field tier, with bronze=B, silver=S, and gold=G.",
                "enum": ["bronze", "silver", "gold"],
            },
            "createdAt": {
                "type": ["string", "null"],
                "format": "date-time",
                "description": "The same account-creation instant represented by source field signed_up.",
            },
            "region": {"type": "string", "description": "ISO market region"},
        },
    },
    separators=(",", ":"),
)


_V4_FULL_CROSSWALK = {
    "summary": "Maps legacy customer identity, name, tier, and signup time; target region is unresolved.",
    "coverage": "PARTIAL",
    "edges": [
        {
            "source_paths": ["/customer_id"],
            "source_types": ["INTEGER"],
            "target_path": "/id",
            "target_type": "STRING",
            "conversion": "TO_STRING",
            "lossiness": "LOSSLESS",
            "null_handling": "REJECT",
            "target_required": True,
            "target_root_required": True,
            "confidence": "HIGH",
            "has_default": False,
            "default_json": "",
            "separator": "",
            "value_map": [],
            "rationale": "Both schema descriptions explicitly identify the fields as the same stable customer identifier and specify the target text encoding.",
        },
        {
            "source_paths": ["/display_name"],
            "source_types": ["STRING"],
            "target_path": "/name",
            "target_type": "STRING",
            "conversion": "RENAME_ONLY",
            "lossiness": "LOSSLESS",
            "null_handling": "REJECT",
            "target_required": True,
            "target_root_required": True,
            "confidence": "HIGH",
            "has_default": False,
            "default_json": "",
            "separator": "",
            "value_map": [],
            "rationale": "Both schema descriptions explicitly identify the fields as the same customer-facing name.",
        },
        {
            "source_paths": ["/tier"],
            "source_types": ["STRING"],
            "target_path": "/level",
            "target_type": "STRING",
            "conversion": "ENUM_TRANSLATION",
            "lossiness": "LOSSLESS",
            "null_handling": "REJECT",
            "target_required": True,
            "target_root_required": True,
            "confidence": "HIGH",
            "has_default": False,
            "default_json": "",
            "separator": "",
            "value_map": [
                {"source_json": '"B"', "target_json": '"bronze"'},
                {"source_json": '"G"', "target_json": '"gold"'},
                {"source_json": '"S"', "target_json": '"silver"'},
            ],
            "rationale": "Both schema descriptions explicitly declare B=bronze, S=silver, and G=gold for the same loyalty level.",
        },
        {
            "source_paths": ["/signed_up"],
            "source_types": ["UNION"],
            "target_path": "/createdAt",
            "target_type": "UNION",
            "conversion": "RENAME_ONLY",
            "lossiness": "LOSSLESS",
            "null_handling": "PRESERVE",
            "target_required": False,
            "target_root_required": False,
            "confidence": "HIGH",
            "has_default": False,
            "default_json": "",
            "separator": "",
            "value_map": [],
            "rationale": "Both schema descriptions explicitly identify the fields as the same account-creation instant.",
        },
    ],
    "unresolved": [
        {
            "side": "TARGET",
            "path": "/region",
            "issue": "MISSING_REQUIRED_INPUT",
            "detail": "The required target region has no source counterpart or specified default.",
        }
    ],
    "assumptions": [],
}


_SEMANTIC_EDGE_KEYS = (
    "source_paths",
    "target_path",
    "conversion",
    "lossiness",
    "null_handling",
    "confidence",
    "default_json",
    "separator",
    "value_map",
)

GOOD_CROSSWALK = {
    "edges": [
        {key: edge[key] for key in _SEMANTIC_EDGE_KEYS}
        for edge in _V4_FULL_CROSSWALK["edges"]
    ],
    "unresolved": [
        {key: item[key] for key in ("side", "path", "issue")}
        for item in _V4_FULL_CROSSWALK["unresolved"]
    ],
}


def mock_good_compile(direct_vm):
    direct_vm.mock_llm(
        r"(?s).*compiling one directional, executable schema crosswalk.*",
        json.dumps(GOOD_CROSSWALK),
    )


def mock_audit(
    direct_vm,
    acceptable=True,
    issues=None,
    issue_code=None,
):
    resolved_issue = issue_code
    if resolved_issue is None:
        resolved_issue = "NONE" if acceptable else (
            issues[0] if issues else "UNSUPPORTED_CORRESPONDENCE"
        )
    direct_vm.mock_llm(
        r"(?s).*SCHEMA_CROSSWALK_SEMANTIC_AUDIT_V6.*",
        json.dumps(
            {
                "verdict": "ACCEPT" if acceptable else "REJECT",
                "issue_code": resolved_issue,
            }
        ),
    )

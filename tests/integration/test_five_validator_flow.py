import json

from gltest import get_contract_factory, get_validator_factory
from gltest.assertions import tx_execution_failed, tx_execution_succeeded
from gltest.contracts.contract import Contract
from gltest.utils import extract_contract_address


SOURCE = json.dumps(
    {
        "title": "EventV1",
        "type": "object",
        "required": ["event_id", "severity"],
        "properties": {
            "event_id": {
                "type": "integer",
                "description": "The same stable event identifier represented by target field id, converted to text.",
            },
            "severity": {
                "type": "string",
                "description": "The same incident severity represented by target priority, with L=low and H=high.",
                "enum": ["L", "H"],
            },
        },
    },
    separators=(",", ":"),
)


TARGET = json.dumps(
    {
        "title": "IncidentV2",
        "type": "object",
        "required": ["id", "priority", "owner"],
        "properties": {
            "id": {
                "type": "string",
                "description": "The same stable event identifier represented by source event_id, encoded as text.",
            },
            "priority": {
                "type": "string",
                "description": "The same incident severity represented by source severity, with low=L and high=H.",
                "enum": ["low", "high"],
            },
            "owner": {"type": "string", "description": "Responsible owner"},
        },
    },
    separators=(",", ":"),
)


_V4_COMPILED = {
    "summary": "Maps event identity and severity; required target owner is unresolved.",
    "coverage": "PARTIAL",
    "edges": [
        {
            "source_paths": ["/event_id"],
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
            "rationale": "Both descriptions explicitly identify the fields as the same stable event identifier and specify text encoding.",
        },
        {
            "source_paths": ["/severity"],
            "source_types": ["STRING"],
            "target_path": "/priority",
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
                {"source_json": '"H"', "target_json": '"high"'},
                {"source_json": '"L"', "target_json": '"low"'},
            ],
            "rationale": "Both descriptions explicitly declare L=low and H=high for the same incident severity.",
        },
    ],
    "unresolved": [
        {
            "side": "TARGET",
            "path": "/owner",
            "issue": "MISSING_REQUIRED_INPUT",
            "detail": "The source schema provides no owner field or defensible default.",
        }
    ],
    "assumptions": [],
}


_SEMANTIC_EDGE_KEYS = {
    "source_paths",
    "target_path",
    "conversion",
    "lossiness",
    "null_handling",
    "confidence",
    "default_json",
    "separator",
    "value_map",
}
COMPILED = {
    "edges": [
        {key: value for key, value in edge.items() if key in _SEMANTIC_EDGE_KEYS}
        for edge in _V4_COMPILED["edges"]
    ],
    "unresolved": [
        {key: item[key] for key in ("side", "path", "issue")}
        for item in _V4_COMPILED["unresolved"]
    ],
}


def _mock_llm(verdict="ACCEPT", issue_code="NONE"):
    return {
        "nondet_exec_prompt": {
            r"(?s).*compiling one directional, executable schema crosswalk.*": json.dumps(COMPILED),
            r"(?s).*SCHEMA_CROSSWALK_SEMANTIC_AUDIT_V6.*": json.dumps(
                {
                    "verdict": verdict,
                    "issue_code": issue_code,
                }
            ),
        },
        "eq_principle_prompt_comparative": {},
        "eq_principle_prompt_non_comparative": {},
    }


def _context():
    validators = get_validator_factory().batch_create_mock_validators(
        count=5,
        mock_llm_response=_mock_llm(),
    )
    return {"validators": [validator.to_dict() for validator in validators]}


def _assert_five_agree(receipt):
    assert tx_execution_succeeded(receipt)
    consensus = receipt["consensus_data"]
    assert len(consensus["validators"]) == 5
    assert len(consensus["votes"]) == 5
    assert set(consensus["votes"].values()) == {"agree"}


def test_five_validator_glsim_end_to_end():
    context = _context()
    factory = get_contract_factory(contract_file_path="schema_crosswalk.py")
    deploy_receipt = factory.deploy_contract_tx(
        args=[],
        transaction_context=context,
        wait_interval=100,
        wait_retries=100,
    )
    _assert_five_agree(deploy_receipt)
    with open("abi.json", "r", encoding="utf-8") as abi_file:
        contract = Contract.new(
            address=extract_contract_address(deploy_receipt),
            schema=json.load(abi_file),
        )

    receipt = contract.compile_pair(args=[SOURCE, TARGET]).transact(
        transaction_context=context,
        wait_interval=100,
        wait_retries=100,
    )
    _assert_five_agree(receipt)

    assert contract.get_record_count(args=[]).call() == 1
    pair_id = contract.get_pair_id_at(args=[0]).call()
    protocol = contract.get_protocol(args=[]).call()
    identity = contract.derive_pair_identity(args=[SOURCE, TARGET]).call()
    metadata = contract.get_metadata(args=[pair_id]).call()
    crosswalk = contract.get_crosswalk(args=[pair_id]).call()

    assert metadata["coverage"] == "PARTIAL"
    assert protocol["compilation_policy_version"] == "schema-crosswalk-exec-policy/6"
    assert protocol["format_version"] == "schema-crosswalk/4"
    assert protocol["model_authored_prose"] is False
    assert protocol["validator_output"] == "CLOSED_VERDICT_AND_ISSUE_CODE_ONLY"
    assert identity["pair_id"] == pair_id
    assert identity["exists"] is True
    assert metadata["edge_count"] == 2
    assert metadata["unresolved_count"] == 1
    assert crosswalk["unresolved"][0]["path"] == "/owner"
    assert crosswalk["unresolved"][0]["detail"] == (
        "Policy-v6 deterministic unresolved classification: MISSING_REQUIRED_INPUT."
    )
    assert all(
        edge["rationale"]
        == "Policy-v6 deterministic rationale: semantic acceptance is established by the "
        "independent full-schema audit."
        for edge in crosswalk["edges"]
    )

    target = contract.find_by_target(args=[pair_id, "/priority"]).call()
    assert target["found"] is True
    assert target["edge"]["conversion"] == "ENUM_TRANSLATION"
    assert contract.matches_fingerprint(
        args=[
            pair_id,
            metadata["crosswalk_hash"],
        ]
    ).call()

    # Canonically equivalent input is a deterministic idempotent no-op.
    second = contract.compile_pair(
        args=[
            json.dumps(json.loads(SOURCE), indent=2, sort_keys=True),
            json.dumps(json.loads(TARGET), indent=4, sort_keys=True),
        ]
    ).transact(transaction_context=context, wait_interval=100, wait_retries=100)
    _assert_five_agree(second)
    assert contract.get_record_count(args=[]).call() == 1

    # An external reference is rejected before any nondeterministic call.
    rejected = contract.compile_pair(
        args=['{"$ref":"https://schemas.example.test/remote.json"}', TARGET]
    ).transact(transaction_context=context, wait_interval=100, wait_retries=100)
    assert tx_execution_failed(rejected)
    assert "only local $ref values" in rejected["consensus_data"]["leader_receipt"][0]["genvm_result"]["stderr"]
    assert contract.get_record_count(args=[]).call() == 1

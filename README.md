# SchemaCrosswalk

SchemaCrosswalk is a standalone reusable GenLayer Intelligent Contract that compiles one directional, executable mapping between two caller-supplied JSON Schemas.

It answers:

> Given these exact source and target schemas, which finite transformations are semantically defensible, what information may be lost, and which explicit fields remain unresolved?

There is no frontend, administrator, ownership role, payment path, arbitrary URL fetch, or off-chain database.

## Why GenLayer is used

Field names alone do not establish meaning. A leader interprets names, descriptions, types, enums, constraints, requiredness, and nesting in both complete schemas. Each validator then substantiates the proposed crosswalk against both schemas. It must reject invented paths, unsupported types, weak semantic correspondences, incomplete enum translations, dishonest lossiness, or material omissions.

Schemas and candidate choices are explicitly delimited as untrusted data. Embedded instructions cannot change the compiler or audit task. Under policy v6, the model returns only nine closed semantic edge fields and three closed unresolved fields. The contract derives types, requiredness, default presence, IDs, rationale, unresolved detail, coverage, summary, assumptions, and counts. The auditor returns exactly `verdict` and `issue_code`; only `ACCEPT` plus `NONE` votes true. A correspondence that needs an external premise must remain unresolved. Consensus is still an evidence-grounded semantic judgment, not a mathematical proof of equivalence.

## Deterministic execution grammar

Every path is a canonical RFC 6901 JSON Pointer over an instance. The root path is `""`; `/customer/id` is nested; `~` and `/` inside field names are encoded as `~0` and `~1`. Only explicit leaf properties are mappable. Arrays are treated as leaf values rather than exposing an index or wildcard extension.

Each stored edge contains ordered `source_paths`, contract-derived aligned source types and requiredness, one `target_path`, its contract-derived target type and requiredness, lossiness, null policy, confidence, typed parameters, a deterministic fixed rationale, and a deterministic edge ID. The model supplies only the closed semantic subset and no prose. Source order is preserved because it changes `CONCATENATE` behavior.

The closed opcode set is:

- `IDENTITY` and `RENAME_ONLY`: copy one same-typed value unchanged;
- `TO_STRING`: convert an integer, number, or boolean to canonical JSON lexical text;
- `TO_INTEGER`: parse a string with JSON base-10 integer grammar;
- `TO_NUMBER`: parse a string with finite JSON number grammar;
- `TO_BOOLEAN`: accept exactly the strings `true` or `false`;
- `ENUM_TRANSLATION`: exact typed lookup with complete coverage of the source enum;
- `CONCATENATE`: join two or more strings in declared path order with a literal separator and no escaping or coercion;
- `CONSTANT`: emit one typed constant without a source path.

There is no generated code, free-form expression, `SPLIT`, `AGGREGATE`, or custom operation in format v4. Anything outside the closed grammar must remain unresolved.

Enum values and defaults use canonical JSON text. This preserves JSON type: `true`, `1`, and `"1"` are different. `has_default` removes sentinel ambiguity, so an empty-string default is represented as `has_default: true` and `default_json: "\"\""`. Defaults are accepted only for `CONSTANT` or `DEFAULT_REQUIRED`; their JSON type, enum, const, numeric bounds, integer `multipleOf`, and string length constraints are checked. Regex `pattern` and structured array/object literals are rejected rather than claimed executable.

## Complete field accounting

The parser deterministically inventories every explicit source and target leaf path plus every string named by `required`. A required name without a property schema becomes `UNKNOWN` and must remain unresolved. Each path must appear in an edge or a matching unresolved entry; mapped and unresolved sets cannot overlap.

- `FULL` requires edges and no unresolved paths.
- `PARTIAL` requires both edges and unresolved paths.
- `NONE` requires no edges and at least one unresolved path.

This prevents vacuous `FULL`/`NONE` results and silent omission of an optional or source-only field. Validators separately audit whether each semantic decision is defensible.

## Atomic references and strict JSON

Inputs are bounded strict JSON objects. Duplicate keys, NULs, non-finite numbers, excessive structure, and every non-local `$ref` form are rejected. `$ref` may be exactly `#` or begin `#/`; its JSON Pointer must resolve inside the same submitted schema, and its object cannot contain sibling keywords. This deliberately narrow rule avoids silently ignoring JSON Schema 2020-12 sibling constraints. Metadata such as a `$schema` URL is inert and does not fetch anything.

## Content-addressed identity

Both schemas are canonicalized with sorted object keys. Identity binds direction, format, and the exact compiler policy:

```text
pair_id = sha256(
  "schema-crosswalk/4" |
  "schema-crosswalk-exec-policy/6" |
  source_hash |
  target_hash
)
```

Whitespace and object-key order do not alter identity. `A -> B` and `B -> A` differ. A repeat submission is an idempotent cache hit and never replaces the immutable accepted record. Any future grammar, prompt, or policy correction requires a new policy/version and therefore a different pair ID.

## ABI

Write:

```text
compile_pair(source_schema_json: str, target_schema_json: str) -> str
```

Views:

```text
get_protocol() -> dict
derive_pair_identity(source_schema_json: str, target_schema_json: str) -> dict
exists(pair_id: str) -> bool
get_record_count() -> u256
get_pair_id_at(index: u256) -> str
get_metadata(pair_id: str) -> dict
get_source_schema(pair_id: str) -> dict
get_target_schema(pair_id: str) -> dict
get_crosswalk(pair_id: str) -> dict
find_by_target(pair_id: str, target_path: str) -> dict
find_by_source(pair_id: str, source_path: str) -> dict
matches_fingerprint(pair_id: str, expected_crosswalk_hash: str) -> bool
```

The machine-readable interface is in [`abi.json`](abi.json).

## Downstream gate

`pair_id` already binds the current format, policy, source hash, and target hash. The compact gate takes only the pair ID and expected crosswalk hash, then recomputes all stored content hashes and identity before returning true:

```python
safe = registry.view().matches_fingerprint(
    pair_id,
    expected_crosswalk_hash,
)
```

They must implement the exact opcode semantics above, validate runtime values, and define which confidence and lossiness classes their application permits.

## Bounds

- 12,000 input characters and 16,000 canonical characters per schema;
- depth 14, 1,400 visited JSON nodes, 256 keys per object, and 256 array items;
- 256 explicit leaf paths per schema and 180 characters per pointer;
- 64 mapping edges, 8 ordered sources per edge, 48 enum pairs, and 64 unresolved entries; model-authored assumptions are not accepted;
- 512 characters per canonical typed JSON literal.
- 64,000 canonical characters for the entire proposed crosswalk.

## Verification

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:PATH = "$PWD\.venv\Scripts;$env:PATH"

genvm-lint check contracts\schema_crosswalk.py
genvm-lint schema contracts\schema_crosswalk.py --output abi.json
genvm-lint typecheck contracts\schema_crosswalk.py --strict
python scripts\build_compact_contract.py --check
pytest tests\build -v
pytest tests\direct -v
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_glsim_tests.ps1
```

The local integration harness uses exactly five mocked validators to verify unanimous-accept consensus plumbing, persisted behavior, idempotence, and deterministic input rejection. The pinned simulator shares one mock response profile across validators, so heterogeneous model-vote behavior is covered by direct captured-validator tests rather than claimed as a GLSim result. It does not prove independent live-model semantic quality. Superseded policy-v1 through policy-v3 StudioNet diagnostics are documented in [`docs/STUDIONET_DIAGNOSTIC.md`](docs/STUDIONET_DIAGNOSTIC.md).

The current audited policy-v6 release is the exact `43,407`-byte contract with SHA-256 `8383D532E3C4CC142369630DA777BC64B5DF10BC1A6640DBCA5C343674B2E7B9`. It retains the 13-method ABI (SHA-256 `17211F17BCA6C8403D71D30B7039AF4379B23A36CFBFAF98047C091E61C50953`). For the packaged four-edge/one-unresolved fixture, its canonical compiler wire falls from 1,603 to 1,041 characters (-562, 35.06%); its representative accepting audit wire falls from 100 to 40 characters (-60, 60.0%). The validator response is exactly two closed fields. Local verification passed 6/6 compact-equivalence tests, strict type checking with 0 diagnostics, 103/103 direct tests, and the 1/1 five-validator GLSim flow. The readable policy-v6 source is `59,302` bytes with SHA-256 `3EF88992C3E87515173B3C57987507AACA29723D44B018C135D3A669AE905124`.

Policy v6 passed independent exact-hash audit and deployed byte-for-byte on both networks. StudioNet finalized the packaged semantic write and stored the expected four-edge, one-unresolved crosswalk with passing fingerprint gates. Bradbury finalized the exact deployment, but its single semantic smoke reached `DISAGREE` through a shared deterministic-violation/runtime path and stored no state. Current v6 evidence is in `deployments/studionet.json` and `deployments/bradbury.json`; v5 and v4 evidence remains preserved in versioned files.

## Limitations

- The schemas are caller claims; the contract does not prove they describe deployed software or an authoritative publisher.
- Explicit `properties` leaves, required names, and locally resolved direct `$ref` targets form the deterministic inventory. Arrays remain leaves. Complex conditional/composition semantics such as `allOf`, `oneOf`, `if/then`, pattern properties, and dynamically named optional fields may need unresolved output even when validators can discuss them.
- The contract compiles mappings but does not execute them or validate runtime instances.
- Sparse, misleading, or adversarial descriptions can still cause correlated model error. Consumers should reject results outside their risk policy.
- StudioNet qualifies the exact v6 artifact and packaged semantic fixture. Bradbury qualifies deployment only: its v6 semantic smoke produced identical successful candidate traces but a deterministic-violation consensus result and zero state.
- The first accepted result for one policy-bound pair is immutable. Pair ID alone does not prove semantic correctness; pin the crosswalk hash too.
- Submitted schemas and compiled records are public on-chain data. Do not submit secrets or personal data.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/AUDIT.md`](docs/AUDIT.md).

## License

MIT. See [`LICENSE`](LICENSE).

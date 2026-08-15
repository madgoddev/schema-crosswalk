# Security and correctness audit

Audit target: `contracts/schema_crosswalk.py`

Contract SHA-256: `8383D532E3C4CC142369630DA777BC64B5DF10BC1A6640DBCA5C343674B2E7B9`

Contract size: `43,407 bytes`

## Current result

**V6 AUDIT GO; STUDIO SEMANTIC PASS; BRADBURY DEPLOYMENT PASS / SEMANTIC RUNTIME-LIMITED.** The compact contract passes independent exact-hash audit, static validation, strict type checking with zero diagnostics, six compact-equivalence/reproducibility tests, 103 direct tests (109 including build tests), and the exactly-five-validator GLSim flow. Its extracted ABI remains 13 methods (12 view, 1 write, no constructor arguments), SHA-256 `17211F17BCA6C8403D71D30B7039AF4379B23A36CFBFAF98047C091E61C50953`. The exact bytes deployed on both networks. StudioNet finalized and stored the packaged semantic result; Bradbury finalized the deployment but its single semantic smoke reached shared deterministic-violation consensus with zero state.

### Compact-source equivalence boundary

The readable policy-v6 source is frozen at [`../reference/schema_crosswalk_policy_v6_readable.py.txt`](../reference/schema_crosswalk_policy_v6_readable.py.txt): 59,302 bytes, SHA-256 `3EF88992C3E87515173B3C57987507AACA29723D44B018C135D3A669AE905124`. The pinned generator proves AST equivalence and alpha-renames 68 collision-checked module-internal bindings. The frozen v5 readable source remains byte-for-byte unchanged at its original path and hash.

Current sanitized v6 evidence is in [`../deployments/studionet.json`](../deployments/studionet.json) and [`../deployments/bradbury.json`](../deployments/bradbury.json). V5 evidence is preserved at [`../deployments/studionet-policy-v5.json`](../deployments/studionet-policy-v5.json) and [`../deployments/bradbury-policy-v5.json`](../deployments/bradbury-policy-v5.json). The prior v4 evidence remains at [`../deployments/studionet-policy-v4.json`](../deployments/studionet-policy-v4.json) and [`../deployments/bradbury-policy-v4.json`](../deployments/bradbury-policy-v4.json) as diagnostic history.

Policy-v1 through policy-v3 StudioNet deployments are diagnostic only. Policy v3 proved live consensus and state storage, then exposed a GenVM read-call decoding failure in its five-dynamic-string gate ABI. It is superseded rather than represented as release evidence. Curated evidence is in [`STUDIONET_DIAGNOSTIC.md`](STUDIONET_DIAGNOSTIC.md).

## Hardened findings

### Ordered multi-source execution

`source_paths` and aligned `source_types` preserve caller-visible order. They are never sorted. `CONCATENATE` is fully defined as literal separator joining of string inputs in that order, without escaping or coercion. `SPLIT` and `AGGREGATE` were removed rather than left under-specified.

### Typed constants, defaults, and enum maps

Constants and fallbacks use `has_default` plus bounded canonical JSON text. JSON type, enum, const, numeric bounds, integer `multipleOf`, and string length constraints are checked. Structured literals and regex-pattern targets are rejected rather than overclaimed. `DEFAULT_REQUIRED` cannot omit its default, and a default cannot appear under another null policy. Enum maps use canonical JSON on both sides, preserve boolean/number/string distinctions, satisfy both field constraints, and must cover every explicit source enum member.

### Canonical path identity

All mapping, unresolved, and lookup paths use validated RFC 6901 JSON Pointer syntax. Invalid escapes, invented leaves, and alternate path languages are rejected. Explicit source and target leaf inventories determine path existence, type, and root-to-leaf target requiredness.

### Atomic references

Every `$ref` must be `#` or begin `#/`, parse as a JSON Pointer, and resolve inside the same submitted schema. Relative files, `file:`, `urn:`, protocol-relative, HTTP, HTTPS, missing local targets, and non-string references are rejected before consensus.

### Deterministic coverage

Every explicit source and target leaf is mapped or unresolved, never both. `FULL`, `PARTIAL`, and `NONE` have non-vacuous deterministic invariants. This prevents a model from silently omitting optional fields or declaring empty work complete.

### Prompt, output-shape liveness, and validator boundary

Both schemas, deterministic inventories, and candidate choices are delimited as untrusted data. Policy v6 accepts exactly nine non-prose edge fields and three non-prose unresolved fields. The contract derives stored rationale, stored unresolved detail, types, local/root requiredness, default presence, edge IDs, coverage, fixed summary, assumptions, and counts. Validators receive only that prose-free semantic projection and return exactly `{verdict, issue_code}`. On the packaged fixture, canonical compiler output is 1,041 instead of 1,603 characters (-562, 35.06%), and a representative accepting audit is 40 instead of 100 characters (-60, 60.0%). Only `ACCEPT` with `NONE` votes true. The full independent audit remains authoritative for correspondence meaning, enum-pair meaning, lossiness, null handling, unresolved classification, ambiguity, material constraints, and prompt-injection resistance.

### Policy-aware cache and downstream gate

Pair identity includes `schema-crosswalk/4` and `schema-crosswalk-exec-policy/6`. Tests prove the same schema hashes cannot reproduce either the policy-v4 or policy-v5 pair ID. A future grammar, prompt, or validator correction must again change policy/version. The two-string `matches_fingerprint(pair_id, expected_crosswalk_hash)` gate fails closed unless the stored format and policy are current, the pair ID recomputes from the stored source and target hashes, all three stored documents recompute to their hashes, and the caller-pinned crosswalk hash matches.

## Threat review and residual limitations

- **Unbounded work:** Raw/canonical schema size, total canonical crosswalk size, depth, nodes, keys, arrays, inventories, pointers, edges, source arity, typed values, enum pairs, and unresolved entries are bounded. Assumptions are forbidden. Maximum-size costs still require network measurement.
- **False evidence:** Content hashes prove the exact submitted schemas, not their authority, freshness, or deployment. The contract fetches nothing.
- **Correlated model error:** Consensus can still accept a plausible semantic mistake or adversarial description. Deterministic checks narrow the result but do not prove equivalence.
- **JSON Schema breadth:** Explicit properties and direct local references are inventoried. Arrays remain leaves. `allOf`, `oneOf`, conditional schemas, dynamic references, pattern properties, and open additional properties are not expanded into executable field paths.
- **Execution scope:** The contract specifies but does not execute operations or validate runtime instances. Consumers must implement the documented grammar exactly and set their own lossiness/confidence policy.
- **Immutable first result:** The first accepted result for one policy-bound schema pair is cached forever. A correction requires a new policy/version or changed evidence. Pair ID alone is insufficient for high assurance; pin the crosswalk hash.
- **Public data:** Submitted schemas and records are public chain data. They must not contain secrets or personal information.
- **Mocked integration semantics:** GLSim uses exactly five validators with a shared mock response profile to prove unanimous-accept voting and state plumbing. The pinned simulator cannot truthfully model heterogeneous validator responses, which are instead tested through direct captured-validator execution. It is not a live-model quality benchmark.
- **Model-output liveness:** The exact templates materially reduce malformed candidate output but cannot guarantee that a live model follows them. Strictly malformed output intentionally fails and forces another consensus attempt rather than storing coerced state.
- **Network qualification:** Exact policy-v6 bytes deployed on both networks. StudioNet finalized the packaged semantic write and full readback. Bradbury finalized deployment, but its single semantic write reached shared deterministic-violation consensus and stored no state; Bradbury semantic qualification therefore remains unavailable.

## Verification matrix

- GenVM AST/SDK validation: pass (3 lint checks; `SchemaCrosswalk`, 13 methods, 12 view and 1 write)
- ABI extraction: pass; unchanged ABI SHA-256 `17211F17BCA6C8403D71D30B7039AF4379B23A36CFBFAF98047C091E61C50953`
- compact-source equivalence and deterministic rebuild: pass (6/6)
- strict Pyright: pass (0 diagnostics)
- direct tests: pass (103/103; 109/109 including build tests)
- five-validator GLSim: pass (1/1; exactly five validators, all agree)
- policy-v6 network deployment: pass on StudioNet and Bradbury with exact source and ABI
- policy-v6 semantic write: StudioNet pass; Bradbury finalized deterministic-violation consensus with zero state
- independent exact-hash audit: pass

## Out of scope

- proving schemas match deployed software;
- fetching external references;
- executing crosswalks or validating instances;
- XML Schema, Protobuf, GraphQL SDL, or arbitrary OpenAPI semantics;
- mathematical proof of semantic completeness or equivalence;
- mainnet deployment approval.

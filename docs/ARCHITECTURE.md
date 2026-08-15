# Architecture and consensus boundary

## Atomic transition

```text
two bounded strict-JSON schemas
  -> reject duplicate keys, non-finite values, non-local/unresolved $ref
  -> canonicalize and hash both documents
  -> enumerate explicit RFC 6901 leaf paths, types, and root-requiredness
  -> derive policy-bound directional pair_id
  -> leader proposes semantic edges plus explicit unresolved paths only
  -> deterministic normalization derives types, requiredness, defaults, rationale, unresolved detail, IDs, coverage, summary, and counts
  -> each validator revalidates canonical form and audits the semantic projection against both full schemas
  -> accepted canonical crosswalk and all fingerprints are stored immutably
```

## Responsibility split

The caller supplies complete public schemas and resolves any external dependency. The caller and downstream executor also choose acceptable confidence/lossiness policies and implement the documented finite opcode semantics.

SchemaCrosswalk owns strict parsing, local-reference resolution, explicit-leaf inventory, content and policy identity, semantic compilation, deterministic execution-grammar checks, validator substantiation, immutable storage, and fingerprint-gated reads.

The contract makes no HTTP request. A `$schema` URL is metadata only. `$ref` is accepted only as `#` or `#/...` when it resolves inside the submitted document.

## Deterministic versus semantic work

Deterministic code establishes:

- exact schema content hashes and policy-bound pair identity;
- canonical RFC 6901 paths and explicit field existence;
- source and target types, immediate-object requiredness, and root-to-leaf requiredness;
- ordered input arity and opcode/type compatibility;
- canonical typed JSON for enum pairs and defaults;
- complete source-enum translation coverage;
- one writer per target path;
- exhaustive mapped-or-unresolved accounting for both inventories, including required names that lack property schemas;
- canonical edge IDs and crosswalk hash.

Validators decide whether names, descriptions, constraints, formats, enum meanings, transformations, null policy, lossiness, confidence, and unresolved reasons are substantively defensible. This separation prevents a structurally valid but schema-free model answer from being stored.

## Untrusted prompt boundary

The source schema, target schema, inventories, and proposed crosswalk are each placed in explicit untrusted-data blocks. Prompts state that descriptions, examples, defaults, embedded roles, and requests to accept are evidence only and cannot change the outer task. Policy v6 gives the leader an exact template of nine closed semantic edge keys and three closed unresolved keys. It permits no model-authored prose: deterministic code supplies the stored rationale and unresolved detail along with every inventory-derived field, and fixes `assumptions` to `[]`.

The leader result is normalized once, then every validator deterministically reconstructs and compares its canonical form before asking a model to audit it. A changed edge ID, path order, count, field, or derived value votes false before semantic acceptance.

Deterministic reconstruction proves types, requiredness, default presence, edge IDs, counts, summary, coverage, assumptions, and exhaustive inventory accounting. Policy v6 removes those echoes and all free text from both model boundaries. Each validator independently judges the remaining semantic boundary and returns exactly `verdict` and one closed `issue_code`. Only `ACCEPT` plus `NONE` votes true. The validator must still reject unsupported correspondences or enum meanings, misleading conversion/lossiness/null claims, undisclosed ambiguity, material ignored constraints, or obedience to embedded instructions. A malformed or inconsistent verdict votes false.

## Closed executable grammar

The format-v4 execution grammar supports only:

```text
IDENTITY, RENAME_ONLY, TO_STRING, TO_INTEGER, TO_NUMBER,
TO_BOOLEAN, ENUM_TRANSLATION, CONCATENATE, CONSTANT
```

There is no arbitrary expression or generated code. Ordered `source_paths` are part of edge identity. `CONCATENATE` uses them in order with one literal separator and no escaping/coercion. Enum pairs and defaults carry canonical JSON text, not lossy string surrogates. Under-specified operations such as `SPLIT`, `AGGREGATE`, date normalization, and custom logic are deliberately absent.

## Storage and correction model

`records` is a `TreeMap[str, str]` of canonical records, `record_ids` is append-only enumeration, and `total_records` is a constant-time count. There is no update, delete, owner, or upgrade method.

`pair_id` includes both format and compilation-policy version plus the source and target hashes. A corrected grammar or prompt requires a policy/version bump, produces a different ID, and cannot silently reinterpret an old cached record. High-assurance consumers call the compact `matches_fingerprint(pair_id, expected_crosswalk_hash)` gate. It recomputes pair identity and source, target, and crosswalk hashes from stored content before accepting the caller's crosswalk fingerprint.

## Scope boundary

The deterministic inventory traverses explicit object `properties`, strings listed by `required`, and locally referenced definitions. A required name without a field schema is an `UNKNOWN` leaf and cannot be mapped. Arrays, scalar roots, recursive boundaries, and objects without explicit properties or required names are treated as leaf values. Conditional and composition keywords remain evidence for validators but are not expanded into an alternative path language. Runtime instance validation and transformation execution are outside this contract.

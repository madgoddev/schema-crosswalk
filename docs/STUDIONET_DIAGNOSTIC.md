# StudioNet diagnostic history

This file records superseded, nonrelease diagnostic deployments. It is not
release evidence and is not evidence that the current policy-v4 source has passed
a live StudioNet smoke test.

## Superseded policy-v3 deployment

- Network: StudioNet (chain ID `61999`)
- Contract source SHA-256: `6A69B8106003C27BC3DD05148341EAF39674363BD9BE7BBD8A1DD4F1CD3AC76D`
- Contract size: `57,017 bytes`
- Deployment transaction: `0x0be672b67b133da2cc34edfcdb3b07c95440a57d160f56c6ba60d3b4d1b69c17`
- Contract: `0x6972885Fcf1d91f67A2308Bf94118CE14d353339`
- Deployment result: `FINALIZED`, `MAJORITY_AGREE`, execution `SUCCESS` (`3` agree, `0` disagree, `2` idle)
- `compile_pair` transaction: `0xe1c152ef1ccb200f195475d8314948088085b12c9750ee6cd1d01070ebf2d834`
- Write result: `FINALIZED`, `MAJORITY_AGREE`, execution `SUCCESS` (`3` agree, `2` disagree)
- Pair ID: `0bc3ccb87d6719e2b14500ff2129dbaf2643387f601c98b135cf919df92ea070`
- Source hash: `2216cd6d9a73157a9b81391244ed1ca160e0a0a3280bab059ff8a92f55418c40`
- Target hash: `ae7a5f4d3fd77c8d6f2fd096999223a2a420980896d6101fb961a69340d13918`
- Crosswalk hash: `128a2b5509bb2543560ba48aeecebc3b9cb0f8c7c038acb388f5d73b22fdaa50`
- Stored result: `PARTIAL`, four edges, one unresolved target

Policy v3 successfully deployed, reached semantic consensus, and stored the
fixture. Its downstream gate nevertheless was not live-call safe. The public
method accepted five dynamic strings. StudioNet returned JSON-RPC `-32603` with
`RLP string ends with 334 superfluous bytes` whenever evaluation reached the
fifth argument; changing the fifth string changed the reported surplus length,
while calls that failed earlier comparisons returned `false`. This isolates a
runtime ABI-decoding defect rather than a bad stored fingerprint. Read-only calls
have no transaction hash.

Policy v4 replaces that ABI with exactly two dynamic strings:
`matches_fingerprint(pair_id, expected_crosswalk_hash)`. The pair ID binds the
current format, policy, source hash, and target hash. The gate independently
recomputes pair identity and all three content hashes before returning true.

## Superseded policy-v2 deployment

- Network: StudioNet (chain ID `61999`)
- Contract source SHA-256: `C7115AAFE16D0A44DD79B3DC979221B80FD678773D951F4A48627C8F3D8B5472`
- Deployment transaction: `0xe5c2af7dd4ebaf1c51ae9aaf17f740b89377096b24ab3451cba924f08848c647`
- Contract: `0x263d6687Cd101dBfA6A7d9AD464aF28816a488Aa`
- Diagnostic `compile_pair` transaction: `0x9ac38572770af5a42ee0ee59072164b0b625cf1b326c34397ea1983bdd57f5c9`
- Transaction lifecycle: `FINALIZED`
- Consensus result: `MAJORITY_DISAGREE`
- Leader execution: `SUCCESS`
- Stored records after the write: `0`

The deployment itself was valid, but the write did not reach validator consensus
and therefore stored no record. Finality alone is not successful execution
evidence. The diagnostic revealed two distinct problems. First, validators were
asked to reproduce edge-ID and full-inventory bookkeeping already enforced by
deterministic code, creating avoidable consensus fragility. Second, the old
fixture inferred that matching nullable date-time shapes represented the same
event and that enum order implied `B/S/G = bronze/silver/gold`; those semantic
links were not explicitly supported by the submitted schemas, so disagreement
could be substantively correct.

Policy v3 removed only the redundant model-echo bookkeeping, kept strict
canonical reconstruction and independent semantic judgment, forbids non-empty
assumptions, and uses a closed `ACCEPT/NONE` verdict protocol. Its packaged
fixture explicitly states every retained correspondence. Direct regressions prove
that the old sparse fixture's aggressive date/enum links are rejected while a
conservative unresolved result can be accepted.

## Superseded policy-v1 deployment

- Network: StudioNet (chain ID `61999`)
- Contract: `0x123f28e27fcC844e25E792841bbc58bab753bd45`
- Deployed source SHA-256: `AF1CC015F656E7152EEFD213CFD4FE1BBC1DB64D12F0101EC252654D96C09756`
- Diagnostic `compile_pair` transaction: `0xe199d7327cef58c843daff7af3569f1f84bc4b8451ae152f685ed9718aa6aa28`
- Transaction lifecycle: `FINALIZED`
- Consensus result: `MAJORITY_DISAGREE`
- Execution result: leader and three validator executions returned
  `[LLM_ERROR] assumption must be a string`

The contract deployment itself was valid, but the diagnostic write failed before
the record write and therefore stored no crosswalk state. A finalized transaction
is not evidence of successful contract execution.

The failure exposed a live-model output-shape ambiguity: the policy-v1 prompt named
`assumptions` but did not explicitly require each item to be a string or provide a
complete typed candidate template. Policy v2 corrected that output shape while
retaining strict parsing; policy v3 additionally forbids assumptions and repairs
the validator boundary described above. Because policy is part of `pair_id`, no
later policy can collide with or reuse a superseded cache domain.

The readable policy-v4 source has SHA-256
`F03B9130581673B93155D676CF9F791CC1CD52ADF81ACE2A7DA643BC9A87CDD0`.
Its independent audit and historical StudioNet deployment and write passed,
but those readable bytes are no longer the current deployment record.

The compact policy-v4 historical release is 43,542 bytes with SHA-256
`40AD05A4EACFF9E7509A7D7B8CC52BFB8E7E2EC85AB4AAA257A909105CCC1F9F`.
It is AST alpha-equivalent, independently audited, and now verified by a fresh
StudioNet deployment and write in [`../deployments/studionet-policy-v4.json`](../deployments/studionet-policy-v4.json).
The same compact bytes deployed successfully on Bradbury, but two bounded write
attempts finalized without state; [`../deployments/bradbury-policy-v4.json`](../deployments/bradbury-policy-v4.json)
records that narrower, network-limited evidence. The historical `F03B...CDD0`
record must not be used as deployment evidence for the compact hash. No private
validator material or raw Studio or Bradbury receipt is retained here.

Policy v5 superseded v4 with a lower-entropy model boundary. The compiler now
returns only semantic edges and unresolved paths; deterministic code derives
types, requiredness, defaults, IDs, coverage, summary, assumptions, and counts.
Validators audit the same semantic projection instead of those derived echoes.
Historical v5 evidence is intentionally separate:
`../deployments/studionet-policy-v5.json` records the finalized StudioNet
deployment and semantic write, while `../deployments/bradbury-policy-v5.json`
records the finalized Bradbury deployment and finalized no-majority, zero-state
smoke.

Policy v6 removes model-authored rationale from the compiler wire and free-text
explanation from the validator wire. Current v6 evidence is
`../deployments/studionet.json` and `../deployments/bradbury.json`. StudioNet
finalized and stored the expected four-edge, one-unresolved crosswalk. Bradbury
deployed exactly, but its single smoke reached a shared deterministic-violation
result with zero state. All exposed v6 Bradbury traces returned identical bytes,
unlike v5's differing candidate hashes; this confirms the free-prose divergence
was removed while leaving a Bradbury-specific deterministic/runtime limitation.

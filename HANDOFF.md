# SchemaCrosswalk handoff

This is a standalone, contract-only GenLayer project. It has no frontend and no
GitHub dependency.

## Frozen audited v6 release

- Contract: `contracts/schema_crosswalk.py`
- SHA-256: `8383D532E3C4CC142369630DA777BC64B5DF10BC1A6640DBCA5C343674B2E7B9`
- Size: 43,407 bytes
- ABI: 13 public methods (12 view, 1 write, 0 constructor parameters)
- ABI SHA-256: `17211F17BCA6C8403D71D30B7039AF4379B23A36CFBFAF98047C091E61C50953`
- Format: `schema-crosswalk/4`
- Compilation policy: `schema-crosswalk-exec-policy/6`
- Readable SHA-256: `3EF88992C3E87515173B3C57987507AACA29723D44B018C135D3A669AE905124`

Local verification passes 6 build tests, 103 direct tests, strict type checking with zero diagnostics, and one exactly-five-validator GLSim flow. Policy v6 reduces the packaged fixture compiler wire by 562 canonical characters (35.06%) and a representative accepting audit by 60 characters (60.0%). Its exact hash was independently audited before deployment. The frozen v5 readable artifact and all v5/v4 deployment evidence remain preserved.

## Network evidence

Policy v6 deployed exactly on both networks. `deployments/studionet.json` records a finalized deployment and finalized semantic smoke with four executable edges, one honest unresolved target, exact content hashes, and a passing fingerprint matrix. `deployments/bradbury.json` records a finalized, exact deployment and a finalized `DISAGREE` semantic smoke with three shared deterministic-violation votes and zero state. No retry, appeal, or manual finalization was submitted.

The v6 Bradbury traces are byte-identical across the exposed rounds, so removal of model-authored rationale and validator explanation fixed the v5 free-prose output divergence. The remaining Bradbury limitation is a shared deterministic-violation/runtime path: the public trace reports zero LLM calls, a default-runner warning, and SIGTERM. Historical v5 records are `deployments/studionet-policy-v5.json` and `deployments/bradbury-policy-v5.json`; policy-v4 files remain diagnostic history.

## Local verification

Run from the extracted project directory:

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

Do not copy a local `.venv`, caches, bytecode, raw receipts, temporary deploy
scripts, or wallet material into the release ZIP.

## Safety boundary

SchemaCrosswalk compiles a bounded mapping; it does not execute it or prove the
schemas are authoritative. Submitted schemas and compiled records are public.
Never submit secrets or personal data. Downstream consumers must pin the network, contract address, exact active policy, finalized state, source hash, target hash, and crosswalk hash, then implement the published closed opcode semantics.

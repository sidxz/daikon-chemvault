# Handoff: ADMET integration in MLogix client

Recap of what shipped in this repo (`daikon-chemvault-api`) during the previous session.
Next step (separate session, working in `/Users/sidx/workspace/daikon/Daikon/src`): wire
the MLogix .NET client to consume the new ADMET surface.

## Context

DAIKON is in sunset mode. ADMET property prediction was added directly to ChemVault
(rather than as a separate microservice) using `swansonk14/admet_ai` v2 — ships ~10
small Chemprop v2 checkpoints inside the wheel, no separate model download. ChemVault
now owns ADMET data and is the single source of truth. MLogix should read through.

Chemvault version bumped to **1.6.0**. Service still on port 10001. Shared docker
network `daikon-be-net` unchanged. No compose-layout changes.

## What chemvault now exposes

### New: `POST /admet/predict`  *(stateless, sync, no persistence)*

Ad-hoc ADMET calculation for arbitrary SMILES. Use for previews of unregistered
molecules — frontend exploration, what-if analysis.

- **Request body:** `["SMILES1", "SMILES2", ...]` — bare list of strings
- **Max 200 SMILES per request** (returns 400 over cap)
- **Response 200:** array in input order, including an entry for invalid SMILES
  (`predictions=null`, `error` filled in)

```json
[
  {
    "smiles": "Cn1c(=O)c2c(ncn2C)n(C)c1=O",
    "predictions": { "BBB_Martins": 0.982, "Bioavailability_Ma": 0.97, ... (~104 keys) },
    "model_version": "2.0.1",
    "error": null
  },
  { "smiles": "***bad***", "predictions": null, "model_version": null,
    "error": "Invalid SMILES (rejected by admet_ai)" }
]
```

Sub-second at small batches (~13 ms/mol after warmup, plus ~5 s one-time model-load tax
on the first request after a container restart — lazy load).

### New: `POST /admet/backfill`  *(async, persists)*

Background backfill across `molecules` for any row without a `done` ADMET prediction.
Returns 202 immediately with pre-run counts.

- Query params: `chunk_size=1000` (1-5000), `limit=N` (optional), `include_errors=false`
- Body: none
- Response 202:
  ```json
  { "queued": true, "chunk_size": 1000, "limit": null, "include_errors": false,
    "pre_counts": { "total_molecules": 15092, "done": 1116, "pending": 0, "error": 0, "missing": 13976 } }
  ```

Self-paginates (rows drop out of the "needs work" filter as they get upserted-pending).
Logged per chunk with rate. Recommended throughput: ~13 ms/mol on the dev box, ~25–40
ms/mol on generic x86_64 prod CPU.

### New: `GET /admet/backfill/status`

Counts breakdown — same shape as `pre_counts` above. Cheap; safe to poll.

### New: `GET /admet/{molecule_id}`

Single persisted ADMET prediction by molecule UUID.

```json
{
  "id": "uuid",
  "status": "done|pending|error",
  "predictions": { ...104 keys... } | null,
  "model_version": "2.0.1" | null,
  "error": null | "..."
}
```

404 if no row exists.

### New: `POST /admet/by-ids`

Bulk persisted ADMET lookup. Body: bare UUID list `["uuid1", "uuid2", ...]`. Response:
`List<AdmetPrediction>`. **Missing IDs are silently omitted** — not 404'd. Caller
correlates by `id` field.

### Changed: `GET /molecules/by-id/{id}` and `POST /molecules/by-ids`

Now embed `admet_prediction` alongside the existing `pains` field:

```json
{
  ...all existing MoleculeBase fields...,
  "pains": { "rdkit_pains": false, "rdkit_pains_label": null },
  "admet_prediction": {
    "id": "uuid", "status": "done",
    "predictions": { ...104 keys... },
    "model_version": "2.0.1", "error": null
  }
}
```

When a molecule has no ADMET row yet, `admet_prediction` is `null` (mirrors the `pains`
pattern). One-extra-query cost via SQLAlchemy `selectin` — `POST /molecules/by-ids`
with 100 IDs costs 2 queries total, not 1 + N.

**Search/list endpoints (`/molecules/by-name`, `/by-smiles-canonical`, `/by-smiles-list`,
`/similarity`, `/substructure`, `/substructure-multiple`, etc.) deliberately do NOT
include `admet_prediction`** — same payload-size pattern as PAINS. To get ADMET for
search results, look up via `POST /admet/by-ids` with the result IDs.

### Behavior change: automatic ADMET on molecule registration

`POST /molecules/` and `POST /molecules/batch` now auto-trigger ADMET as a background
task **only for genuinely new molecules** (not idempotent lookups, synonym merges, or
preview mode). Same async-side-effect pattern PAINS uses.

**HTTP contracts unchanged** — request/response schemas byte-identical to before;
verified via OpenAPI spec. The trigger is server-side; downstream callers don't need
to know about it. **No changes needed to the existing Register / RegisterBatch DTOs
or methods on the .NET side.** ADMET appears later (via the GET endpoints) without
any extra registration-time work.

## What was deliberately NOT done (still open)

1. **MLogix .NET client + DTOs** — this work, next session.
2. **Aggregators** — no changes. If aggregator queries need ADMET, that's follow-up.
3. **Frontend** — `daikon-chemvault-fe` untouched.
4. **Search-endpoint ADMET embed** — kept light intentionally. Easy to widen later.
5. **Per-property hot columns / indexes** — JSONB only. No SQL-level filtering on
   individual ADMET properties.

## Suggested MLogix integration shape

Existing pattern at `Daikon/src/Services/MLogix/`:

- **Interface:** `MLogix.Application/Contracts/Infrastructure/DaikonChemVault/IMoleculeAPI.cs`
- **DTOs:** `MLogix.Application/DTOs/DaikonChemVault/MoleculeBase.cs`, `PainsVM.cs`
- **Client (partial classes):** `MLogix.Infrastructure/DaikonChemVault/MoleculeAPI_*.cs`
  — one file per feature (`_GET`, `_Register`, `_Similarity`, `_Substructure`, `_Molcal`,
  `_Batch`, `_Update`, `_Delete`, `_BASE`)
- **DI:** `MLogix.Infrastructure/InfrastructureServiceRegistration.cs:48` —
  `services.AddScoped<IMoleculeAPI, MoleculeAPI>()`

Mirror that pattern for ADMET. Concretely:

### 1. New DTO `MLogix.Application/DTOs/DaikonChemVault/AdmetVM.cs`

```csharp
using System.Text.Json.Serialization;

namespace MLogix.Application.DTOs.DaikonChemVault
{
    public class AdmetVM
    {
        [JsonPropertyName("id")]
        public Guid Id { get; set; }

        [JsonPropertyName("status")]
        public string Status { get; set; } = "";

        [JsonPropertyName("predictions")]
        public Dictionary<string, object> Predictions { get; set; }

        [JsonPropertyName("model_version")]
        public string ModelVersion { get; set; }

        [JsonPropertyName("error")]
        public string Error { get; set; }
    }

    public class AdmetCalcResult
    {
        [JsonPropertyName("smiles")]
        public string Smiles { get; set; } = "";

        [JsonPropertyName("predictions")]
        public Dictionary<string, object> Predictions { get; set; }

        [JsonPropertyName("model_version")]
        public string ModelVersion { get; set; }

        [JsonPropertyName("error")]
        public string Error { get; set; }
    }
}
```

### 2. Add field to `MoleculeBase.cs`

`MoleculeBase.cs:122-123` already has `[JsonPropertyName("pains")] public PainsVM Pains`.
Add right after it:

```csharp
[JsonPropertyName("admet_prediction")]
public AdmetVM AdmetPrediction { get; set; }
```

Auto-populates whenever `GetMoleculeById` / `GetMoleculesByIds` deserialize a response,
since chemvault now embeds it.

### 3. Extend `IMoleculeAPI.cs`

Add to the interface:

```csharp
Task<List<AdmetCalcResult>> PredictAdmet(List<string> smilesList, IDictionary<string, string> headers);
Task<AdmetVM> GetAdmetByMoleculeId(Guid registrationId, IDictionary<string, string> headers);
Task<List<AdmetVM>> GetAdmetByMoleculeIds(List<Guid> registrationIds, IDictionary<string, string> headers);
```

Recommend **leaving backfill trigger out of the MLogix client** — it's an ops/maintenance
operation; invoke via `curl` directly against chemvault when needed.

### 4. New client partial `MLogix.Infrastructure/DaikonChemVault/MoleculeAPI_Admet.cs`

Mirror `MoleculeAPI_Molcal.cs` exactly — same `SendRequestAsync` plumbing from
`MoleculeAPI_BASE.cs`. URLs:
- `POST {_apiBaseUrl}/admet/predict` — body: `List<string>`
- `GET  {_apiBaseUrl}/admet/{registrationId}`
- `POST {_apiBaseUrl}/admet/by-ids` — body: `List<Guid>`

### 5. Application layer

Interface-level work is enough to give consumers (queries / aggregators / frontend BFF)
the ability to read ADMET. Whether to add a MediatR query handler like
`GetMoleculeAdmetByIdQuery` is a judgment call — match what's done for PAINS. If PAINS
is just used via the embedded field on molecule responses, no extra handler needed
for the embedded case.

## Gotchas / things to know

- **Sunset framing.** No need to over-engineer. JSONB blob is fine; per-property
  queryability is explicitly out of scope.
- **Caches.** ADMET DTOs are large (~104 numeric properties + percentiles). If MLogix
  caches molecule reads anywhere, entries will grow noticeably. Acceptable.
- **First-call latency on a cold container.** First request after chemvault restart pays
  a ~5 s model-load tax (logged as `Loading admet_ai model`). Subsequent requests reuse
  the singleton. If MLogix has a startup smoke test, calling `POST /admet/predict` with
  one SMILES at boot amortizes this.
- **CPU-only torch.** Chemvault is pinned to the CPU torch wheel (`pytorch-cpu` index
  in chemvault's Pipfile). Even on a GPU host, ADMET runs on CPU. At ~13 ms/molecule
  that's fast enough for everything .NET will throw at it.
- **Async on registration.** New molecules get ADMET via a background task. Between the
  `POST /molecules/` 200 and ADMET appearing in `admet_prediction`, there's a ~200 ms
  gap (longer on first call). If MLogix immediately follows registration with a
  `GetMoleculeById`, `admet_prediction` may still be `null` or `status="pending"`.
  Standard eventual-consistency pattern; callers should tolerate it.
- **`AdmetVM.Predictions` keys** — stable but long. Roughly 50 properties each with a
  `_drugbank_approved_percentile` mirror, plus physchem (logP, MW, TPSA, Lipinski, etc.)
  → ~104 total. Examples: `BBB_Martins`, `Bioavailability_Ma`, `CYP2C19_Veith`,
  `BBB_Martins_drugbank_approved_percentile`. Treat as opaque dict downstream.

## Quick sanity-check commands

```bash
# Predict stateless (no persistence)
curl -s -X POST http://localhost:10001/admet/predict \
  -H 'Content-Type: application/json' \
  -d '["Cn1c(=O)c2c(ncn2C)n(C)c1=O","CC(=O)Oc1ccccc1C(=O)O"]' | jq

# Read embed via molecules endpoint (caffeine UUID for reference)
curl -s http://localhost:10001/molecules/by-id/d3b97e83-1625-4752-868c-322ff23ac869 | jq '.admet_prediction'

# Bulk read by ids
curl -s -X POST http://localhost:10001/admet/by-ids \
  -H 'Content-Type: application/json' \
  -d '["d3b97e83-1625-4752-868c-322ff23ac869"]' | jq

# Backfill status / kick-off (ops-only)
curl -s http://localhost:10001/admet/backfill/status | jq
curl -s -X POST 'http://localhost:10001/admet/backfill?chunk_size=1000'
```

OpenAPI / Swagger UI at `http://localhost:10001/docs` for the full live spec.

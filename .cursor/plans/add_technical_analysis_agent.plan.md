---
name: Add Technical Analysis Agent
overview: Integrate the existing PSXTechnicalAgent into the Next.js dashboard via a bridge script, API route, and UI—following the fundamental analysis pattern.
todos: []
---

# Add Technical Analysis Agent — Step by Step

## Context

- **Agent**: [psx_technical_agent.py](psx_technical_agent.py) — `PSXTechnicalAgent` with `analyze_symbol(symbol)` and `analyze_batch(symbols)`; requires [psx_price_store.py](psx_price_store.py) for price data.
- **Returns**: `TechnicalSnapshot` — signals, overall_bias, confidence, indicator_values (RSI, MACD, SMA, etc.).
- **Pattern**: Same as fundamental: [scripts/api_fundamental.py](scripts/api_fundamental.py) + [src/app/api/analysis/fundamental/route.ts](src/app/api/analysis/fundamental/route.ts) + [src/components/dashboard/FundamentalAnalysis.tsx](src/components/dashboard/FundamentalAnalysis.tsx).

---

## Step 1: Create the bridge script

**File**: `scripts/api_technical.py`

1. Add shebang and docstring; import `sys`, `os`, `json`, `datetime`.
2. Insert project root into `sys.path`: `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`.
3. Import from `psx_price_store`: `PSXPriceStore`; from `psx_technical_agent`: `PSXTechnicalAgent`, `TechnicalSnapshot`, `TechnicalSignal`, `SignalType`, `SignalStrength`.
4. Define `DEFAULT_SYMBOLS` (e.g. `["LUCK", "PSO", "HBL", "ENGRO", "MCB", "OGDC", "PPL", "UBL", "HUBC", "FFC"]`).
5. Implement `snapshot_to_dict(snapshot: TechnicalSnapshot)`:
   - For each signal: dict with symbol, date, indicator, signal_type (enum `.value`), strength (enum `.value`), value, threshold, description.
   - Return dict: symbol, date, signals (list), overall_bias (`.value`), confidence, indicator_values; if snapshot has divergences/patterns, serialize to simple lists/dicts or omit for now.
6. In `main()`:
   - Read `mode = (sys.argv[1] or "single").strip().lower()`; allow only `single` or `batch`.
   - Read symbol arg from `sys.argv[2]`; for single mode require symbol; for batch use comma-split or DEFAULT_SYMBOLS.
7. In `main()` (continued):
   - Create `PSXPriceStore()` (default db path).
   - Create `PSXTechnicalAgent(price_store)`.
   - If single: call `agent.analyze_symbol(symbol)`, set `data = snapshot_to_dict(snapshot)`.
   - If batch: call `agent.analyze_batch(symbols_list)`, set `data = { "results": { sym: snapshot_to_dict(s) for sym, s in results.items() }, "symbols_analyzed": len(symbols_list) }`.
8. Print JSON: `{ "success": true, "data": data, "timestamp": datetime.now().isoformat() }`. Wrap in try/except; on exception print `{ "success": false, "error": str(e) }` and `sys.exit(1)`.

---

## Step 2: Create the API route

**File**: `src/app/api/analysis/technical/route.ts`

1. Import `NextRequest`, `NextResponse` from `next/server`; `spawn` from `child_process`; `path` from `path`.
2. Set `export const maxDuration = 90`.
3. In `GET` handler: read `mode` (default `single`) and `symbol` / `symbols` from `searchParams`; validate mode is `single` or `batch`; for single require `symbol`, for batch allow empty symbols (use default in script).
4. Resolve `pythonCmd` from `process.env.PYTHON_PATH` or `process.platform === "win32" ? "py" : "python3"`.
5. Set `scriptPath = path.join(process.cwd(), "scripts", "api_technical.py")`; build `args = [scriptPath, mode]` then push symbol or symbols string.
6. Return a Promise that spawns process with `spawn(pythonCmd, args, { cwd: process.cwd(), timeout: 120000 })`, collect stdout/stderr.
7. On `close`: if code !== 0, return 500 with error; else parse JSON from stdout; if `result.success` return `NextResponse.json(result)`, else 500 with result.error.
8. On parse error or `proc.on("error")`, return 500 with a clear message.

---

## Step 3: Add dashboard nav and page

1. **Layout**: In [src/app/dashboard/layout.tsx](src/app/dashboard/layout.tsx), add to the `nav` array (e.g. after Fundamental): `{ href: "/dashboard/technical", label: "Technical Analysis", icon: "📉" }`.
2. **Page**: Create `src/app/dashboard/technical/page.tsx`: import `TechnicalAnalysis` from `@/components/dashboard/TechnicalAnalysis`; render a heading "Technical Analysis", a short description (e.g. "Indicators and signals from PSXTechnicalAgent"), and `<TechnicalAnalysis />`.

---

## Step 4: Create the UI component

**File**: `src/components/dashboard/TechnicalAnalysis.tsx`

1. Use client component: `"use client"`; import `useState`; import Card, Button, Input, Label, Badge, Skeleton (or similar) from your UI library.
2. Define types for API response: single result (symbol, date, overall_bias, confidence, signals[], indicator_values), and batch result (results: Record&lt;string, single&gt;, symbols_analyzed).
3. State: `mode` (single | batch), `symbol` (string), `symbols` (string), `loading`, `error`, `singleResult` (single snapshot or null), `batchResult` (batch payload or null).
4. Implement fetch: for single `fetch(\`/api/analysis/technical?mode=single&symbol=${encodeURIComponent(symbol)}\`)`, for batch `fetch(\`/api/analysis/technical?mode=batch&symbols=${encodeURIComponent(symbols || DEFAULT)}\`)`; set loading/error/results from response.
5. Render:
   - Mode toggle or select (Single / Batch).
   - Single: input for symbol, "Run analysis" button; when result, show symbol, date, bias badge, confidence, table of indicator_values, list of signals (indicator, type, strength, description).
   - Batch: optional symbols input; button; when result, table of symbols with overall_bias, confidence, and key indicators (e.g. RSI); optionally expand or link to show full snapshot.
   - Show Skeleton while loading; show error message when error.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Create `scripts/api_technical.py` (path, imports, snapshot_to_dict, main with single/batch, JSON out). |
| 2 | Create `src/app/api/analysis/technical/route.ts` (GET, spawn script, parse JSON, return or 500). |
| 3 | Add nav item in layout; create `src/app/dashboard/technical/page.tsx`. |
| 4 | Create `src/components/dashboard/TechnicalAnalysis.tsx` (form, fetch, display single/batch results). |

No new dependencies. Optional later: persist snapshots via `TechnicalStore` in the bridge script; add multi-timeframe or overbought/oversold screens.

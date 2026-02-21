"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type TechnicalSignalItem = {
  symbol: string;
  date: string;
  indicator: string;
  signal_type: string;
  strength: string;
  value: number;
  threshold?: number | null;
  description: string;
};

type FibonacciLevels = {
  swing_high?: number;
  swing_low?: number;
  trend?: string;
  levels?: Record<string, number>;
  current_price?: number;
};

type ElliottWave = {
  phase?: string;
  direction?: number;
  confidence?: number;
  wave_label?: string;
};

type TechnicalSnapshotResult = {
  symbol: string;
  date: string;
  signals: TechnicalSignalItem[];
  overall_bias: string;
  confidence: number;
  indicator_values: Record<string, number>;
  trend_score?: number;
  mean_reversion_score?: number;
  technical_score?: number;
  divergences?: unknown[];
  patterns?: unknown[];
  fibonacci_levels?: FibonacciLevels | null;
  elliott_wave?: ElliottWave | null;
  ai_summary?: string | null;
  ai_call?: string | null;
  ai_call_rationale?: string | null;
};

type BatchData = {
  results: Record<string, TechnicalSnapshotResult>;
  symbols_analyzed: number;
};

type MTFData = {
  symbol: string;
  date: string;
  daily: TechnicalSnapshotResult;
  weekly: TechnicalSnapshotResult;
  confirmation_score: number;
  aligned_signals: string[];
  conflicting_signals: string[];
};

type ScreenData = {
  results: Record<string, TechnicalSnapshotResult>;
  symbols_analyzed: number;
  symbols_matching: number;
  filter: string;
};

const DEFAULT_SYMBOLS_STR = "LUCK,PSO,HBL,ENGRO,MCB,OGDC,PPL,UBL,HUBC,FFC";

const biasStyle: Record<string, string> = {
  Bullish: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
  Bearish: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
  Neutral: "bg-muted text-muted-foreground border-border",
  Overbought: "bg-amber-500/20 text-amber-700 dark:text-amber-400 border-amber-500/30",
  Oversold: "bg-blue-500/20 text-blue-700 dark:text-blue-400 border-blue-500/30",
};

function fmtVal(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return typeof v === "number" && !Number.isInteger(v) ? v.toFixed(2) : String(v);
}

function SnapshotCard({
  snapshot,
  title,
}: {
  snapshot: TechnicalSnapshotResult;
  title: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <p className="text-sm text-muted-foreground">
          Date: {snapshot.date} · Confidence: {(snapshot.confidence * 100).toFixed(0)}%
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-4">
          <Badge
            className={
              biasStyle[snapshot.overall_bias] ?? "bg-muted text-muted-foreground"
            }
          >
            {snapshot.overall_bias}
          </Badge>
          <div
            className="h-4 rounded-full bg-muted overflow-hidden flex-1 min-w-[120px] max-w-[200px]"
            role="progressbar"
            aria-valuenow={snapshot.confidence * 100}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div
              className="h-full bg-primary transition-all"
              style={{ width: `${Math.min(100, snapshot.confidence * 100)}%` }}
            />
          </div>
        </div>
        {(snapshot.technical_score != null ||
          snapshot.trend_score != null ||
          snapshot.mean_reversion_score != null) && (
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div className="rounded border p-2">
              <span className="text-muted-foreground">Technical </span>
              <span className="font-medium tabular-nums">{snapshot.technical_score ?? "—"}</span>
            </div>
            <div className="rounded border p-2">
              <span className="text-muted-foreground">Trend </span>
              <span className="font-medium tabular-nums">{snapshot.trend_score ?? "—"}</span>
            </div>
            <div className="rounded border p-2">
              <span className="text-muted-foreground">Mean rev </span>
              <span className="font-medium tabular-nums">{snapshot.mean_reversion_score ?? "—"}</span>
            </div>
          </div>
        )}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
          {Object.entries(snapshot.indicator_values ?? {}).map(([key, val]) => (
            <div
              key={key}
              className="rounded border p-2 flex justify-between items-center text-xs"
            >
              <span className="text-muted-foreground">{key}</span>
              <span className="font-mono tabular-nums">{fmtVal(val)}</span>
            </div>
          ))}
        </div>
        {snapshot.fibonacci_levels && (
          <div className="rounded-lg border p-3 space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Fibonacci</p>
            <div className="flex flex-wrap gap-2 text-xs">
              <span>Trend: {snapshot.fibonacci_levels.trend ?? "—"}</span>
              <span>Swing H/L: {fmtVal(snapshot.fibonacci_levels.swing_high)} / {fmtVal(snapshot.fibonacci_levels.swing_low)}</span>
              {snapshot.fibonacci_levels.levels && Object.entries(snapshot.fibonacci_levels.levels).map(([k, v]) => (
                <span key={k} className="font-mono">{k.replace("Fib_Retrace_", "")}: {fmtVal(v)}</span>
              ))}
            </div>
          </div>
        )}
        {snapshot.elliott_wave && (
          <div className="rounded-lg border p-3 space-y-1">
            <p className="text-sm font-medium text-muted-foreground">Elliott Wave</p>
            <p className="text-sm">{snapshot.elliott_wave.wave_label ?? snapshot.elliott_wave.phase ?? "—"}</p>
            <p className="text-xs text-muted-foreground">Confidence: {snapshot.elliott_wave.confidence != null ? `${(snapshot.elliott_wave.confidence * 100).toFixed(0)}%` : "—"}</p>
          </div>
        )}
        <div className="rounded-lg border p-3 space-y-2 bg-muted/30">
          <p className="text-sm font-medium text-muted-foreground">AI technical summary</p>
          <p className="text-sm">{snapshot.ai_summary || "No summary available."}</p>
          <p className="text-sm font-semibold">
            Call: <span className={snapshot.ai_call === "Buy" ? "text-green-600 dark:text-green-400" : snapshot.ai_call === "Sell" ? "text-red-600 dark:text-red-400" : "text-amber-600 dark:text-amber-400"}>{snapshot.ai_call || "—"}</span>
          </p>
          <p className="text-xs text-muted-foreground">{snapshot.ai_call_rationale || "No rationale available."}</p>
        </div>
        {snapshot.signals?.length > 0 && (
          <ul className="space-y-1 text-sm">
            {snapshot.signals.map((s, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2 border-b border-border/50 pb-1 last:border-0">
                <Badge variant="outline" className={biasStyle[s.signal_type] ?? "bg-muted"}>
                  {s.indicator}
                </Badge>
                <span>{s.signal_type}</span>
                <span className="font-mono tabular-nums">{fmtVal(s.value)}</span>
                {s.description && <span className="text-muted-foreground">— {s.description}</span>}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export function TechnicalAnalysis() {
  const [mode, setMode] = useState<"single" | "batch" | "mtf" | "screen">("single");
  const [symbol, setSymbol] = useState("OGDC");
  const [symbols, setSymbols] = useState("");
  const [screenFilter, setScreenFilter] = useState<"both" | "overbought" | "oversold">("both");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [singleResult, setSingleResult] = useState<TechnicalSnapshotResult | null>(null);
  const [batchResult, setBatchResult] = useState<BatchData | null>(null);
  const [mtfResult, setMtfResult] = useState<MTFData | null>(null);
  const [screenResult, setScreenResult] = useState<ScreenData | null>(null);

  const runAnalysis = () => {
    setLoading(true);
    setError(null);
    setSingleResult(null);
    setBatchResult(null);
    setMtfResult(null);
    setScreenResult(null);

    if (mode === "single") {
      const sym = symbol.trim().toUpperCase().replace(".KA", "");
      if (!sym) {
        setError("Enter a symbol");
        setLoading(false);
        return;
      }
      const params = new URLSearchParams({ mode: "single", symbol: sym });
      fetch(`/api/analysis/technical?${params}`)
        .then((r) => r.json())
        .then((res) => {
          if (res.success && res.data && !res.data.results) {
            setSingleResult(res.data as TechnicalSnapshotResult);
          } else {
            const msg = res.error ?? "Analysis failed";
            setError(res.details ? `${msg}: ${res.details}` : msg);
          }
        })
        .catch((e) => setError(e.message ?? "Request failed"))
        .finally(() => setLoading(false));
      return;
    }

    if (mode === "mtf") {
      const sym = symbol.trim().toUpperCase().replace(".KA", "");
      if (!sym) {
        setError("Enter a symbol");
        setLoading(false);
        return;
      }
      const params = new URLSearchParams({ mode: "mtf", symbol: sym });
      fetch(`/api/analysis/technical?${params}`)
        .then((r) => r.json())
        .then((res) => {
          if (res.success && res.data?.daily != null) {
            setMtfResult(res.data as MTFData);
          } else {
            const msg = res.error ?? "MTF analysis failed";
            setError(res.details ? `${msg}: ${res.details}` : msg);
          }
        })
        .catch((e) => setError(e.message ?? "Request failed"))
        .finally(() => setLoading(false));
      return;
    }

    if (mode === "screen") {
      const syms = symbols.trim() || DEFAULT_SYMBOLS_STR;
      const params = new URLSearchParams({
        mode: "screen",
        symbols: syms,
        filter: screenFilter,
      });
      fetch(`/api/analysis/technical?${params}`)
        .then((r) => r.json())
        .then((res) => {
          if (res.success && res.data?.results != null) {
            setScreenResult(res.data as ScreenData);
          } else {
            const msg = res.error ?? "Screen failed";
            setError(res.details ? `${msg}: ${res.details}` : msg);
          }
        })
        .catch((e) => setError(e.message ?? "Request failed"))
        .finally(() => setLoading(false));
      return;
    }

    const syms = symbols.trim() || DEFAULT_SYMBOLS_STR;
    const params = new URLSearchParams({ mode: "batch", symbols: syms });
    fetch(`/api/analysis/technical?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.results != null) {
          setBatchResult(res.data as BatchData);
        } else {
          const msg = res.error ?? "Analysis failed";
          setError(res.details ? `${msg}: ${res.details}` : msg);
        }
      })
      .catch((e) => setError(e.message ?? "Request failed"))
      .finally(() => setLoading(false));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Run technical analysis</CardTitle>
          <p className="text-sm text-muted-foreground">
            PSXTechnicalAgent computes RSI, MACD, SMA crossovers, Bollinger Bands,
            Stochastic, ATR, OBV and aggregates an overall bias. Single symbol or
            batch (comma-separated; leave empty for default list).
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant={mode === "single" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode("single")}
            >
              Single
            </Button>
            <Button
              type="button"
              variant={mode === "batch" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode("batch")}
            >
              Batch
            </Button>
            <Button
              type="button"
              variant={mode === "mtf" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode("mtf")}
            >
              Multi-timeframe
            </Button>
            <Button
              type="button"
              variant={mode === "screen" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode("screen")}
            >
              Overbought/Oversold
            </Button>
          </div>
          {(mode === "single" || mode === "mtf") && (
            <div className="space-y-2">
              <Label>Symbol</Label>
              <Input
                placeholder="e.g. OGDC"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                className="w-32 uppercase"
              />
            </div>
          )}
          {(mode === "batch" || mode === "screen") && (
            <div className="space-y-2">
              <Label>Symbols (comma-separated, or leave empty for default)</Label>
              <Input
                placeholder={DEFAULT_SYMBOLS_STR}
                value={symbols}
                onChange={(e) => setSymbols(e.target.value)}
                className="w-64"
              />
            </div>
          )}
          {mode === "screen" && (
            <div className="space-y-2">
              <Label>Filter</Label>
              <div className="flex gap-2">
                {(["both", "overbought", "oversold"] as const).map((f) => (
                  <Button
                    key={f}
                    type="button"
                    variant={screenFilter === f ? "default" : "outline"}
                    size="sm"
                    onClick={() => setScreenFilter(f)}
                  >
                    {f === "both" ? "Both" : f === "overbought" ? "Overbought only" : "Oversold only"}
                  </Button>
                ))}
              </div>
            </div>
          )}
          <Button onClick={runAnalysis} disabled={loading}>
            {loading ? "Analyzing…" : mode === "screen" ? "Screen" : mode === "mtf" ? "Run MTF" : "Analyze"}
          </Button>
        </CardContent>
      </Card>

      {loading && (
        <Card>
          <CardContent className="pt-6">
            <Skeleton className="h-8 w-48 mb-4" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-full mb-2" />
            <Skeleton className="h-4 w-3/4" />
          </CardContent>
        </Card>
      )}

      {error && (
        <Card className="border-destructive/50">
          <CardContent className="pt-6 text-destructive">{error}</CardContent>
        </Card>
      )}

      {singleResult && !loading && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {singleResult.symbol} — Technical snapshot
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Date: {singleResult.date} · Confidence:{" "}
                {(singleResult.confidence * 100).toFixed(0)}%
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-4">
                <Badge
                  className={
                    biasStyle[singleResult.overall_bias] ??
                    "bg-muted text-muted-foreground"
                  }
                >
                  {singleResult.overall_bias}
                </Badge>
                <div
                  className="h-4 rounded-full bg-muted overflow-hidden flex-1 min-w-[120px] max-w-[200px]"
                  role="progressbar"
                  aria-valuenow={singleResult.confidence * 100}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="h-full bg-primary transition-all"
                    style={{
                      width: `${Math.min(100, singleResult.confidence * 100)}%`,
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-primary/20 bg-muted/20">
            <CardHeader>
              <CardTitle>AI technical summary & call</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-muted-foreground">
                {singleResult.ai_summary || "No summary available."}
              </p>
              <p className="font-semibold">
                Call:{" "}
                <span
                  className={
                    singleResult.ai_call === "Buy"
                      ? "text-green-600 dark:text-green-400"
                      : singleResult.ai_call === "Sell"
                        ? "text-red-600 dark:text-red-400"
                        : "text-amber-600 dark:text-amber-400"
                  }
                >
                  {singleResult.ai_call || "—"}
                </span>
              </p>
              <p className="text-xs text-muted-foreground">
                {singleResult.ai_call_rationale || "No rationale available."}
              </p>
            </CardContent>
          </Card>

          {(singleResult.technical_score != null ||
            singleResult.trend_score != null ||
            singleResult.mean_reversion_score != null) && (
            <Card>
              <CardHeader>
                <CardTitle>Scores (1–100)</CardTitle>
                <p className="text-sm text-muted-foreground">
                  50 = neutral · Above 50 = bullish strength · Below 50 = bearish
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="rounded-lg border p-4">
                    <p className="text-xs text-muted-foreground mb-1">
                      Overall technical
                    </p>
                    <p className="text-2xl font-bold tabular-nums">
                      {singleResult.technical_score ?? 50}
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-xs text-muted-foreground mb-1">
                      Trend following
                    </p>
                    <p className="text-sm text-muted-foreground mb-0.5">
                      MACD, SMA crossover, SMA 200
                    </p>
                    <p className="text-2xl font-bold tabular-nums">
                      {singleResult.trend_score ?? 50}
                    </p>
                  </div>
                  <div className="rounded-lg border p-4">
                    <p className="text-xs text-muted-foreground mb-1">
                      Mean reversion
                    </p>
                    <p className="text-sm text-muted-foreground mb-0.5">
                      RSI, Bollinger Bands, Stochastic
                    </p>
                    <p className="text-2xl font-bold tabular-nums">
                      {singleResult.mean_reversion_score ?? 50}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Indicator values</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
                {Object.entries(singleResult.indicator_values ?? {}).map(
                  ([key, val]) => (
                    <div
                      key={key}
                      className="rounded-lg border p-2 flex justify-between items-center"
                    >
                      <span className="text-xs text-muted-foreground">{key}</span>
                      <span className="font-mono text-sm tabular-nums">
                        {fmtVal(val)}
                      </span>
                    </div>
                  )
                )}
              </div>
              {(!singleResult.indicator_values ||
                Object.keys(singleResult.indicator_values).length === 0) && (
                <p className="text-sm text-muted-foreground">
                  No indicator data (insufficient price history or no signals).
                </p>
              )}
            </CardContent>
          </Card>

          {singleResult.signals?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Signals</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {singleResult.signals.map((s, i) => (
                    <li
                      key={i}
                      className="flex flex-wrap items-center gap-2 text-sm border-b border-border pb-2 last:border-0 last:pb-0"
                    >
                      <Badge
                        variant="outline"
                        className={
                          biasStyle[s.signal_type] ?? "bg-muted text-muted-foreground"
                        }
                      >
                        {s.indicator}
                      </Badge>
                      <span>{s.signal_type}</span>
                      <span className="text-muted-foreground">({s.strength})</span>
                      <span className="font-mono tabular-nums">{fmtVal(s.value)}</span>
                      {s.description && (
                        <span className="text-muted-foreground">
                          — {s.description}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {batchResult && !loading && (
        <Card>
          <CardHeader>
            <CardTitle>Batch results</CardTitle>
            <p className="text-sm text-muted-foreground">
              {batchResult.symbols_analyzed} symbols analyzed
            </p>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 font-medium">Symbol</th>
                    <th className="text-left py-2 font-medium">Bias</th>
                    <th className="text-left py-2 font-medium">Score</th>
                    <th className="text-left py-2 font-medium">Trend</th>
                    <th className="text-left py-2 font-medium">Mean Rev</th>
                    <th className="text-left py-2 font-medium">Confidence</th>
                    <th className="text-left py-2 font-medium">RSI</th>
                    <th className="text-left py-2 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(batchResult.results).map(([sym, snap]) => (
                    <tr key={sym} className="border-b border-border/50">
                      <td className="py-2 font-medium">{sym}</td>
                      <td className="py-2">
                        <Badge
                          className={
                            biasStyle[snap.overall_bias] ??
                            "bg-muted text-muted-foreground"
                          }
                        >
                          {snap.overall_bias}
                        </Badge>
                      </td>
                      <td className="py-2 tabular-nums font-medium">
                        {snap.technical_score ?? "—"}
                      </td>
                      <td className="py-2 tabular-nums text-muted-foreground">
                        {snap.trend_score ?? "—"}
                      </td>
                      <td className="py-2 tabular-nums text-muted-foreground">
                        {snap.mean_reversion_score ?? "—"}
                      </td>
                      <td className="py-2 tabular-nums">
                        {(snap.confidence * 100).toFixed(0)}%
                      </td>
                      <td className="py-2 tabular-nums">
                        {fmtVal(snap.indicator_values?.RSI)}
                      </td>
                      <td className="py-2 text-muted-foreground">{snap.date}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {mtfResult && !loading && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Timeframe confirmation</CardTitle>
              <p className="text-sm text-muted-foreground">
                {mtfResult.symbol} · Daily vs weekly alignment
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-4">
                <div className="min-w-[120px]">
                  <p className="text-xs text-muted-foreground mb-1">Confirmation score</p>
                  <div
                    className="h-4 rounded-full bg-muted overflow-hidden flex-1 min-w-[120px] max-w-[200px]"
                    role="progressbar"
                    aria-valuenow={mtfResult.confirmation_score * 100}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className="h-full bg-primary transition-all"
                      style={{
                        width: `${Math.min(100, mtfResult.confirmation_score * 100)}%`,
                      }}
                    />
                  </div>
                  <p className="text-sm font-medium tabular-nums mt-1">
                    {(mtfResult.confirmation_score * 100).toFixed(0)}%
                  </p>
                </div>
              </div>
              {mtfResult.aligned_signals.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Aligned</p>
                  <ul className="text-sm list-disc list-inside space-y-0.5">
                    {mtfResult.aligned_signals.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
              {mtfResult.conflicting_signals.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">Conflicting</p>
                  <ul className="text-sm list-disc list-inside space-y-0.5 text-amber-600 dark:text-amber-400">
                    {mtfResult.conflicting_signals.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SnapshotCard snapshot={mtfResult.daily} title="Daily snapshot" />
            <SnapshotCard snapshot={mtfResult.weekly} title="Weekly snapshot" />
          </div>
        </div>
      )}

      {screenResult && !loading && (
        <Card>
          <CardHeader>
            <CardTitle>Overbought / Oversold screen</CardTitle>
            <p className="text-sm text-muted-foreground">
              {screenResult.symbols_matching} of {screenResult.symbols_analyzed} symbols match
              (filter: {screenResult.filter})
            </p>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left py-2 font-medium">Symbol</th>
                    <th className="text-left py-2 font-medium">Bias</th>
                    <th className="text-left py-2 font-medium">RSI</th>
                    <th className="text-left py-2 font-medium">Matching signals</th>
                    <th className="text-left py-2 font-medium">Confidence</th>
                    <th className="text-left py-2 font-medium">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(screenResult.results).map(([sym, snap]) => {
                    const obOsSignals = (snap.signals ?? []).filter(
                      (s) => s.signal_type === "Overbought" || s.signal_type === "Oversold"
                    );
                    return (
                      <tr key={sym} className="border-b border-border/50">
                        <td className="py-2 font-medium">{sym}</td>
                        <td className="py-2">
                          <Badge
                            className={
                              biasStyle[snap.overall_bias] ??
                              "bg-muted text-muted-foreground"
                            }
                          >
                            {snap.overall_bias}
                          </Badge>
                        </td>
                        <td className="py-2 tabular-nums">
                          {fmtVal(snap.indicator_values?.RSI)}
                        </td>
                        <td className="py-2">
                          <span className="flex flex-wrap gap-1">
                            {obOsSignals.map((s, i) => (
                              <Badge
                                key={i}
                                variant="outline"
                                className={biasStyle[s.signal_type] ?? "bg-muted"}
                              >
                                {s.indicator}: {s.signal_type}
                              </Badge>
                            ))}
                          </span>
                        </td>
                        <td className="py-2 tabular-nums">
                          {(snap.confidence * 100).toFixed(0)}%
                        </td>
                        <td className="py-2 text-muted-foreground">{snap.date}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {Object.keys(screenResult.results).length === 0 && (
              <p className="text-sm text-muted-foreground py-4">
                No symbols with overbought/oversold signals for this filter.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

export function TechnicalResultCard({ ticker }: { ticker: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TechnicalSnapshotResult | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setResult(null);
    const params = new URLSearchParams({ mode: "single", symbol: ticker });
    fetch(`/api/analysis/technical?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data && !res.data.results) {
          setResult(res.data as TechnicalSnapshotResult);
        } else {
          setError(res.error ?? "Analysis failed");
        }
      })
      .catch((e) => setError(e.message ?? "Request failed"))
      .finally(() => setLoading(false));
  }, [ticker]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Technical Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-16 w-full mt-4" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle>Technical Analysis</CardTitle>
        </CardHeader>
        <CardContent className="text-destructive">{error}</CardContent>
      </Card>
    );
  }

  if (!result) return null;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Technical snapshot</CardTitle>
          <p className="text-sm text-muted-foreground">
            Date: {result.date} · Confidence: {(result.confidence * 100).toFixed(0)}%
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-4">
            <Badge className={biasStyle[result.overall_bias] ?? "bg-muted text-muted-foreground"}>
              {result.overall_bias}
            </Badge>
            <div
              className="h-4 rounded-full bg-muted overflow-hidden flex-1 min-w-[120px] max-w-[200px]"
              role="progressbar"
              aria-valuenow={result.confidence * 100}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${Math.min(100, result.confidence * 100)}%` }}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {(result.technical_score != null || result.trend_score != null || result.mean_reversion_score != null) && (
        <Card>
          <CardHeader>
            <CardTitle>Scores (1–100)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="rounded-lg border p-4">
                <p className="text-xs text-muted-foreground mb-1">Overall technical</p>
                <p className="text-2xl font-bold tabular-nums">{result.technical_score ?? 50}</p>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-xs text-muted-foreground mb-1">Trend following</p>
                <p className="text-2xl font-bold tabular-nums">{result.trend_score ?? 50}</p>
              </div>
              <div className="rounded-lg border p-4">
                <p className="text-xs text-muted-foreground mb-1">Mean reversion</p>
                <p className="text-2xl font-bold tabular-nums">{result.mean_reversion_score ?? 50}</p>
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
            {Object.entries(result.indicator_values ?? {}).map(([key, val]) => (
              <div key={key} className="rounded-lg border p-2 flex justify-between items-center">
                <span className="text-xs text-muted-foreground">{key}</span>
                <span className="font-mono text-sm tabular-nums">{fmtVal(val)}</span>
              </div>
            ))}
          </div>
          {(!result.indicator_values || Object.keys(result.indicator_values).length === 0) && (
            <p className="text-sm text-muted-foreground">No indicator data.</p>
          )}
        </CardContent>
      </Card>

      {result.fibonacci_levels && (
        <Card>
          <CardHeader>
            <CardTitle>Fibonacci</CardTitle>
            <p className="text-sm text-muted-foreground">
              Trend: {result.fibonacci_levels.trend ?? "—"} · Swing H/L: {fmtVal(result.fibonacci_levels.swing_high)} / {fmtVal(result.fibonacci_levels.swing_low)}
            </p>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2 text-sm">
              {result.fibonacci_levels.levels && Object.entries(result.fibonacci_levels.levels).map(([k, v]) => (
                <span key={k} className="rounded border px-2 py-1 font-mono text-xs">{k.replace("Fib_Retrace_", "")}: {fmtVal(v)}</span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {result.elliott_wave && (
        <Card>
          <CardHeader>
            <CardTitle>Elliott Wave</CardTitle>
            <p className="text-sm text-muted-foreground">
              {result.elliott_wave.wave_label ?? result.elliott_wave.phase ?? "—"} · Confidence: {result.elliott_wave.confidence != null ? `${(result.elliott_wave.confidence * 100).toFixed(0)}%` : "—"}
            </p>
          </CardHeader>
        </Card>
      )}

      <Card className="border-primary/20 bg-muted/20">
        <CardHeader>
          <CardTitle>AI technical summary & call</CardTitle>
          <p className="text-sm text-muted-foreground">{result.ai_summary || "No summary available."}</p>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="font-semibold">
            Call: <span className={result.ai_call === "Buy" ? "text-green-600 dark:text-green-400" : result.ai_call === "Sell" ? "text-red-600 dark:text-red-400" : "text-amber-600 dark:text-amber-400"}>{result.ai_call || "—"}</span>
          </p>
          <p className="text-sm text-muted-foreground">{result.ai_call_rationale || "No rationale available."}</p>
        </CardContent>
      </Card>

      {result.signals?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Signals</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {result.signals.map((s, i) => (
                <li key={i} className="flex flex-wrap items-center gap-2 text-sm border-b border-border pb-2 last:border-0 last:pb-0">
                  <Badge variant="outline" className={biasStyle[s.signal_type] ?? "bg-muted text-muted-foreground"}>
                    {s.indicator}
                  </Badge>
                  <span>{s.signal_type}</span>
                  <span className="text-muted-foreground">({s.strength})</span>
                  <span className="font-mono tabular-nums">{fmtVal(s.value)}</span>
                  {s.description && <span className="text-muted-foreground">— {s.description}</span>}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

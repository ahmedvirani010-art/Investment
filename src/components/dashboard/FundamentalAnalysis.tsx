"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type Valuation = {
  pe_ratio?: number | null;
  pb_ratio?: number | null;
  dividend_yield?: number | null;
  ev_ebitda?: number | null;
  price_to_sales?: number | null;
  enterprise_value?: number | null;
};

type FinancialHealth = {
  debt_to_equity?: number | null;
  current_ratio?: number | null;
  quick_ratio?: number | null;
  roa?: number | null;
  roe?: number | null;
  interest_coverage?: number | null;
  operating_cash_flow?: number | null;
};

type GrowthMetrics = {
  revenue_growth_yoy?: number | null;
  earnings_growth_yoy?: number | null;
  revenue_cagr_3y?: number | null;
  earnings_cagr_3y?: number | null;
  margin_trend?: string | null;
  margin_change_pct?: number | null;
};

type MomentumMetrics = {
  earnings_surprise_pct?: number | null;
  estimate_revision_trend?: number | null;
  upcoming_catalysts?: string[];
};

type RedFlagItem = {
  flag: string;
  severity: string;
  action: string;
  description: string;
};

type FundamentalResult = {
  symbol: string;
  fundamental_score: number;
  recommendation: string;
  confidence: string;
  valuation: Valuation;
  financial_health: FinancialHealth;
  growth_metrics: GrowthMetrics;
  momentum_metrics: MomentumMetrics;
  red_flags: RedFlagItem[];
  catalysts: string[];
  analyst_consensus?: string | null;
  fair_value?: number | null;
  upside_pct?: number | null;
  data_timestamp?: string;
  data_quality?: number;
  valuation_score: number;
  health_score: number;
  growth_score: number;
  momentum_score: number;
  processing_time_ms?: number | null;
  analysis_mode: string;
  research_report?: string | null;
};

const recommendationStyle: Record<string, string> = {
  BUY: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
  HOLD: "bg-amber-500/20 text-amber-700 dark:text-amber-400 border-amber-500/30",
  SELL: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
};

const severityStyle: Record<string, string> = {
  critical: "bg-red-600/30 text-red-800 dark:text-red-300 border-red-600/50",
  high: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
  medium: "bg-amber-500/20 text-amber-700 dark:text-amber-400 border-amber-500/30",
  low: "bg-muted text-muted-foreground border-border",
};

function fmtNum(v: number | null | undefined): string {
  if (v == null) return "—";
  return Number.isInteger(v) ? String(v) : v.toFixed(2);
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v.toFixed(1)}%`;
}

export function FundamentalAnalysis() {
  const [symbol, setSymbol] = useState("OGDC");
  const [mode, setMode] = useState<"quick" | "deep">("quick");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<FundamentalResult | null>(null);

  const runAnalysis = () => {
    const sym = symbol.trim().toUpperCase().replace(".KA", "");
    if (!sym) {
      setError("Enter a symbol");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    const params = new URLSearchParams({ mode, symbol: sym });
    fetch(`/api/analysis/fundamental?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data && !res.data.results) {
          setResult(res.data as FundamentalResult);
        } else if (res.success && res.data?.results) {
          setError("Screen mode returns multiple results; use single-symbol quick/deep for this view.");
        } else {
          setError(res.error ?? "Analysis failed");
        }
      })
      .catch((e) => setError(e.message ?? "Request failed"))
      .finally(() => setLoading(false));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Single-symbol analysis</CardTitle>
          <p className="text-sm text-muted-foreground">
            Fundamental analysis (PSXFundamentalAgent). Quick uses cache; deep
            fetches fresh data, runs peer/DCF enhancement, and when{" "}
            <code className="text-xs bg-muted px-1 rounded">ANTHROPIC_API_KEY</code>{" "}
            is set, runs the full LLM research pipeline (company, industry, financial, news briefings).
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="space-y-2">
            <Label>Symbol</Label>
            <Input
              placeholder="e.g. OGDC"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-32 uppercase"
            />
          </div>
          <div className="space-y-2">
            <Label>Mode</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={mode === "quick" ? "default" : "outline"}
                size="sm"
                onClick={() => setMode("quick")}
              >
                Quick
              </Button>
              <Button
                type="button"
                variant={mode === "deep" ? "default" : "outline"}
                size="sm"
                onClick={() => setMode("deep")}
              >
                Deep
              </Button>
            </div>
          </div>
          <Button onClick={runAnalysis} disabled={loading}>
            {loading ? "Analyzing…" : "Analyze"}
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

      {result && !loading && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                {result.symbol} — Fundamental score
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Mode: {result.analysis_mode}
                {result.processing_time_ms != null &&
                  ` · ${result.processing_time_ms} ms`}
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex items-baseline gap-2">
                  <span className="text-3xl font-bold tabular-nums">
                    {result.fundamental_score.toFixed(1)}
                  </span>
                  <span className="text-muted-foreground">/ 100</span>
                </div>
                <div
                  className="h-4 rounded-full bg-muted overflow-hidden flex-1 min-w-[120px] max-w-[200px]"
                  role="progressbar"
                  aria-valuenow={result.fundamental_score}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="h-full bg-primary transition-all"
                    style={{ width: `${Math.min(100, result.fundamental_score)}%` }}
                  />
                </div>
                <Badge
                  className={
                    recommendationStyle[result.recommendation] ??
                    "bg-muted text-muted-foreground"
                  }
                >
                  {result.recommendation}
                </Badge>
                <Badge variant="outline">{result.confidence}</Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Component scores</CardTitle>
              <p className="text-sm text-muted-foreground">
                Valuation 30% · Financial health 40% · Growth 20% · Momentum
                10%
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground mb-1">
                    Valuation
                  </p>
                  <p className="text-xl font-semibold tabular-nums">
                    {result.valuation_score.toFixed(0)}
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground mb-1">Health</p>
                  <p className="text-xl font-semibold tabular-nums">
                    {result.health_score.toFixed(0)}
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground mb-1">Growth</p>
                  <p className="text-xl font-semibold tabular-nums">
                    {result.growth_score.toFixed(0)}
                  </p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground mb-1">Momentum</p>
                  <p className="text-xl font-semibold tabular-nums">
                    {result.momentum_score.toFixed(0)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Valuation</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  P/E: {fmtNum(result.valuation.pe_ratio)} · P/B:{" "}
                  {fmtNum(result.valuation.pb_ratio)}
                </p>
                <p>
                  Div yield: {fmtPct(result.valuation.dividend_yield)} ·
                  EV/EBITDA: {fmtNum(result.valuation.ev_ebitda)}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Financial health</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p>
                  D/E: {fmtNum(result.financial_health.debt_to_equity)} ·
                  Current ratio: {fmtNum(result.financial_health.current_ratio)}
                </p>
                <p>
                  ROA: {fmtPct(result.financial_health.roa)} · ROE:{" "}
                  {fmtPct(result.financial_health.roe)}
                </p>
                <p>
                  Interest coverage:{" "}
                  {fmtNum(result.financial_health.interest_coverage)}x
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Growth</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                Revenue growth YoY:{" "}
                {fmtPct(result.growth_metrics.revenue_growth_yoy)} · Earnings
                growth YoY:{" "}
                {fmtPct(result.growth_metrics.earnings_growth_yoy)}
              </p>
              <p>Margin trend: {result.growth_metrics.margin_trend ?? "—"}</p>
            </CardContent>
          </Card>

          {(result.red_flags?.length ?? 0) > 0 && (
            <Card className="border-amber-500/30">
              <CardHeader>
                <CardTitle>Red flags</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {result.red_flags.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <Badge
                        className={
                          severityStyle[r.severity] ?? "bg-muted text-muted-foreground"
                        }
                      >
                        {r.severity}
                      </Badge>
                      <span>{r.description}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {(result.catalysts?.length ?? 0) > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Catalysts</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="list-disc list-inside space-y-1 text-sm">
                  {result.catalysts.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {(result.fair_value != null || result.upside_pct != null) && (
            <Card>
              <CardHeader>
                <CardTitle>Price target</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-6 text-sm">
                {result.fair_value != null && (
                  <p>Fair value: {fmtNum(result.fair_value)}</p>
                )}
                {result.upside_pct != null && (
                  <p>Upside: {fmtPct(result.upside_pct)}</p>
                )}
                {result.data_quality != null && (
                  <p className="text-muted-foreground">
                    Data quality: {fmtPct(result.data_quality * 100)}
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {result.research_report && (
            <Card>
              <CardHeader>
                <CardTitle>Research report</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="whitespace-pre-wrap text-sm font-sans bg-muted/50 p-4 rounded-md overflow-auto max-h-96">
                  {result.research_report}
                </pre>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

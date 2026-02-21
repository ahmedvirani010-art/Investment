"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type RegimeSummaryRow = {
  state: number;
  mean_return: number;
  volatility: number;
  count: number;
};

type RegimeRiskMetrics = {
  current_regime_volatility: number;
  suggested_stop_pct: number;
  risk_level: string;
};

type HMMData = {
  symbol: string;
  period: string;
  interval: string;
  n_components: number;
  last_state: number;
  backend?: string; // "hmmlearn" | "gmm"
  summary: RegimeSummaryRow[];
  states: number[];
  timestamps: string[];
  close_prices: number[];
  state_probabilities?: number[];
  last_confidence?: number;
  risk?: RegimeRiskMetrics;
};

const STATE_COLORS = [
  "#22c55e", "#ef4444", "#3b82f6", "#f59e0b", "#8b5cf6",
  "#ec4899", "#14b8a6",
];

type HMMRegimeAnalysisProps = {
  apiPath?: string;
  defaultSymbol?: string;
  defaultPeriod?: string;
  defaultInterval?: string;
  defaultNComponents?: number;
  title?: string;
  description?: string;
  /** When set, show an Asset dropdown for quick selection (e.g. the 7 assets). */
  assetPresets?: { label: string; symbol: string }[];
};

export function HMMRegimeAnalysis({
  apiPath = "/api/analysis/hmm-regime",
  defaultSymbol = "BTC-USD",
  defaultPeriod = "730d",
  defaultInterval = "1h",
  defaultNComponents = 7,
  title,
  description,
  assetPresets,
}: HMMRegimeAnalysisProps = {}) {
  const [symbol, setSymbol] = useState(defaultSymbol);
  const [period, setPeriod] = useState(defaultPeriod);
  const [interval, setInterval] = useState(defaultInterval);
  const [nComponents, setNComponents] = useState(defaultNComponents);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<HMMData | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const params = new URLSearchParams({
        symbol: symbol.trim() || defaultSymbol,
        period: period.trim() || defaultPeriod,
        interval: interval.trim() || defaultInterval,
        n_components: String(nComponents),
        last_n: "500",
      });
      const res = await fetch(`${apiPath}?${params}`);
      const json = await res.json();
      if (!res.ok) {
        const msg = [json.error, json.details].filter(Boolean).join(" — ");
        setError(msg || "Request failed");
        return;
      }
      if (!json.success || !json.data) {
        const msg = [json.error, json.details].filter(Boolean).join(" — ");
        setError(msg || "No data returned");
        return;
      }
      setData(json.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const chartData =
    data?.timestamps?.map((t, i) => ({
      time: t,
      label: new Date(t).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
      }),
      close: data.close_prices[i],
      state: data.states[i],
    })) ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{title ?? "Parameters"}</CardTitle>
          <p className="text-sm text-muted-foreground mb-2">
            {description ??
              "Gaussian HMM on returns, range (high-low)/close, and volume change. Any yfinance symbol (e.g. BTC-USD, LUCK.PK)."}
          </p>
          <div className="text-xs text-muted-foreground rounded-md bg-muted/60 p-3 space-y-1">
            <p className="font-medium text-foreground">To run true HMM (recommended, in order):</p>
            <ol className="list-decimal list-inside space-y-0.5 ml-1">
              <li>Use <strong>Python 3.11 or 3.12</strong> (3.14 needs C++ Build Tools for hmmlearn).</li>
              <li>Create a venv: <code className="rounded bg-muted px-1">py -3.12 -m venv .venv</code> then <code className="rounded bg-muted px-1">.\.venv\Scripts\Activate.ps1</code></li>
              <li>Install: <code className="rounded bg-muted px-1">pip install hmmlearn scikit-learn yfinance</code></li>
              <li>Set <code className="rounded bg-muted px-1">PYTHON_PATH=.venv\Scripts\python.exe</code> in <code className="rounded bg-muted px-1">.env</code> so the dashboard uses this Python.</li>
            </ol>
            <p className="pt-1">See <code className="rounded bg-muted px-1">docs/HMM_SETUP.md</code> for details. Without hmmlearn, GMM fallback is used.</p>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          {assetPresets && assetPresets.length > 0 && (
            <div className="space-y-2">
              <Label>Asset</Label>
              <Select
                value={
                  assetPresets.find((p) => p.symbol === symbol)?.symbol ?? "__other__"
                }
                onValueChange={(val) => {
                  if (val && val !== "__other__") setSymbol(val);
                }}
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Select asset" />
                </SelectTrigger>
                <SelectContent>
                  {assetPresets.map((p) => (
                    <SelectItem key={p.symbol} value={p.symbol}>
                      {p.label}
                    </SelectItem>
                  ))}
                  <SelectItem value="__other__">Other (type below)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="hmm-symbol">Symbol</Label>
            <Input
              id="hmm-symbol"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="BTC-USD"
              className="w-32"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="hmm-period">Period</Label>
            <Input
              id="hmm-period"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              placeholder="730d"
              className="w-24"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="hmm-interval">Interval</Label>
            <Input
              id="hmm-interval"
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
              placeholder="1h"
              className="w-20"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="hmm-n">States</Label>
            <Input
              id="hmm-n"
              type="number"
              min={2}
              max={15}
              value={nComponents}
              onChange={(e) => setNComponents(Number(e.target.value) || 7)}
              className="w-20"
            />
          </div>
          <Button onClick={runAnalysis} disabled={loading}>
            {loading ? "Running…" : "Run HMM"}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading && !data && (
        <Card>
          <CardContent className="pt-6">
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          <div className="flex flex-wrap items-center gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Current regime</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Badge
                  style={{
                    backgroundColor: STATE_COLORS[data.last_state % STATE_COLORS.length] + "30",
                    color: STATE_COLORS[data.last_state % STATE_COLORS.length],
                    borderColor: STATE_COLORS[data.last_state % STATE_COLORS.length],
                  }}
                >
                  State {data.last_state}
                </Badge>
                <p className="text-sm text-muted-foreground">
                  Confidence:{" "}
                  {typeof data.last_confidence === "number" && !Number.isNaN(data.last_confidence) ? (
                    <span className="font-medium text-foreground">
                      {Math.round(data.last_confidence * 100)}%
                    </span>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </p>
                {data.risk && (
                  <div className="pt-2 border-t border-border/50 space-y-1 text-sm text-muted-foreground">
                    <p>Regime vol: <span className="font-medium text-foreground tabular-nums">{(data.risk.current_regime_volatility * 100).toFixed(4)}%</span></p>
                    <p>Suggested stop: <span className="font-medium text-foreground tabular-nums">{data.risk.suggested_stop_pct.toFixed(2)}%</span></p>
                    <p>Risk level: <Badge variant={data.risk.risk_level === "high" ? "destructive" : data.risk.risk_level === "low" ? "default" : "secondary"} className="ml-0.5">{data.risk.risk_level}</Badge></p>
                  </div>
                )}
              </CardContent>
            </Card>
            {data.backend && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Model</CardTitle>
                </CardHeader>
                <CardContent>
                  <Badge
                    variant={data.backend === "hmmlearn" ? "default" : "secondary"}
                    className={data.backend === "hmmlearn" ? "bg-green-600" : ""}
                  >
                    {data.backend === "hmmlearn"
                      ? "Gaussian HMM (hmmlearn)"
                      : "Regime clustering (GMM fallback)"}
                  </Badge>
                </CardContent>
              </Card>
            )}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Regime summary</CardTitle>
              <p className="text-sm text-muted-foreground">
                Mean return and volatility by hidden state (sorted by mean return).
              </p>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 pr-4">State</th>
                      <th className="text-right py-2 pr-4">Mean return</th>
                      <th className="text-right py-2 pr-4">Volatility</th>
                      <th className="text-right py-2">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.summary.map((row) => (
                      <tr key={row.state} className="border-b border-border/50">
                        <td className="py-2 pr-4">
                          <span
                            className="inline-block w-3 h-3 rounded-full mr-2 align-middle"
                            style={{
                              backgroundColor: STATE_COLORS[row.state % STATE_COLORS.length],
                            }}
                          />
                          {row.state}
                        </td>
                        <td className="text-right py-2 pr-4 tabular-nums">
                          {(row.mean_return * 100).toFixed(4)}%
                        </td>
                        <td className="text-right py-2 pr-4 tabular-nums">
                          {(row.volatility * 100).toFixed(4)}%
                        </td>
                        <td className="text-right py-2 tabular-nums">{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {chartData.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>{data.symbol} — Price by regime (last {chartData.length} bars)</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Gray line: close price. Points colored by HMM state.
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-[360px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={chartData}
                      margin={{ top: 8, right: 8, left: 0, bottom: 8 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                      <XAxis
                        dataKey="label"
                        tick={{ fontSize: 10 }}
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        domain={["auto", "auto"]}
                        tick={{ fontSize: 10 }}
                        tickFormatter={(v) =>
                          typeof v === "number" && v >= 1000
                            ? `${(v / 1000).toFixed(1)}k`
                            : String(v)
                        }
                      />
                      <Tooltip
                        content={({ active, payload }) => {
                          if (!active || !payload?.length) return null;
                          const p = payload[0].payload;
                          return (
                            <div className="rounded-md border border-border bg-card px-3 py-2 text-sm shadow">
                              <div>{p.label}</div>
                              <div>Close: {typeof p.close === "number" ? p.close.toFixed(2) : p.close}</div>
                              <div>
                                State:{" "}
                                <span
                                  style={{
                                    color: STATE_COLORS[p.state % STATE_COLORS.length],
                                  }}
                                >
                                  {p.state}
                                </span>
                              </div>
                            </div>
                          );
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="close"
                        stroke="hsl(var(--muted-foreground))"
                        strokeWidth={1}
                        dot={(props) => {
                          const { cx, cy, payload } = props;
                          if (cx == null || cy == null) return null;
                          const color =
                            STATE_COLORS[Number(payload?.state) % STATE_COLORS.length] ?? "#888";
                          return (
                            <circle
                              cx={cx}
                              cy={cy}
                              r={2.5}
                              fill={color}
                              stroke="none"
                            />
                          );
                        }}
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

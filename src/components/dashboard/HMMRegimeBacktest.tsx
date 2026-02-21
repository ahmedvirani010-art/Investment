"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

type BacktestData = {
  current_signal: string;
  current_regime: string;
  bull_state_id: number;
  bear_state_id: number;
  timestamps: string[];
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  states: number[];
  equity_curve: number[];
  trades: Array<{
    entry_time: string;
    exit_time: string;
    entry_price: number;
    exit_price: number;
    return_pct: number;
    leveraged_return_pct: number;
    side?: "long" | "short";
  }>;
  total_return_pct: number;
  buy_hold_return_pct: number;
  alpha_pct: number;
  win_rate: number;
  max_drawdown_pct: number;
};

const BULL_COLOR = "#22c55e";
const BEAR_COLOR = "#ef4444";
const LAST_N = 500;

function formatNetworkError(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e);
  const lower = msg.toLowerCase();
  if (
    lower.includes("refused") ||
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("network request failed")
  ) {
    return "Connection refused. Make sure the Next.js dev server is running (e.g. npm run dev).";
  }
  return msg || "Request failed";
}

type OptimizeResult = {
  best_params: {
    cooldown_hours?: number;
    leverage?: number;
    min_confirmations?: number;
    n_components?: number;
  };
  best_value: number | null;
  n_trials: number;
  n_completed_ok?: number;
  metric: string;
  symbol: string;
  period: string;
  interval: string;
  trials_summary: Array<{
    number: number;
    value: number | null;
    params: Record<string, unknown>;
  }>;
};

export function HMMRegimeBacktest() {
  const [symbol, setSymbol] = useState("BTC-USD");
  const [period, setPeriod] = useState("730d");
  const [interval, setInterval] = useState("1h");
  const [nComponents, setNComponents] = useState(7);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<BacktestData | null>(null);

  const [loadingOptimize, setLoadingOptimize] = useState(false);
  const [optimizeError, setOptimizeError] = useState<string | null>(null);
  const [optimizeResult, setOptimizeResult] = useState<OptimizeResult | null>(null);

  const [appliedCooldownHours, setAppliedCooldownHours] = useState<number | null>(null);
  const [appliedLeverage, setAppliedLeverage] = useState<number | null>(null);
  const [appliedMinConfirmations, setAppliedMinConfirmations] = useState<number | null>(null);
  const [allowShort, setAllowShort] = useState(false);
  const [appliedMinBearConfirmations, setAppliedMinBearConfirmations] = useState<number | null>(null);

  const [loadingWalkForward, setLoadingWalkForward] = useState(false);
  const [walkForwardError, setWalkForwardError] = useState<string | null>(null);
  const [walkForwardData, setWalkForwardData] = useState<{
    folds: Array<{ fold: number; test_start: string; test_end: string; total_return_pct: number; buy_hold_return_pct: number; alpha_pct: number; n_trades: number }>;
    mean_return_pct: number;
    std_return_pct: number;
    min_return_pct: number;
    max_return_pct: number;
    mean_alpha_pct: number;
    wins_vs_bh: number;
    n_folds: number;
  } | null>(null);

  const runBacktest = async () => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const params = new URLSearchParams({
        symbol: symbol.trim() || "BTC-USD",
        period: period.trim() || "730d",
        interval: interval.trim() || "1h",
        n_components: String(nComponents),
      });
      if (appliedCooldownHours != null) params.set("cooldown_hours", String(appliedCooldownHours));
      if (appliedLeverage != null) params.set("leverage", String(appliedLeverage));
      if (appliedMinConfirmations != null) params.set("min_confirmations", String(appliedMinConfirmations));
      if (allowShort) params.set("allow_short", "true");
      if (allowShort && appliedMinBearConfirmations != null) params.set("min_bear_confirmations", String(appliedMinBearConfirmations));
      const res = await fetch(`/api/analysis/hmm-regime-backtest?${params}`);
      const json = await res.json();
      if (!res.ok) {
        const msg = [json.error, json.details].filter(Boolean).join(" — ");
        const display =
          msg && msg.toLowerCase().includes("refused")
            ? `${msg} Make sure the dev server is running (npm run dev).`
            : msg || "Request failed";
        setError(display);
        return;
      }
      if (!json.success || !json.data) {
        const msg = [json.error, json.details].filter(Boolean).join(" — ");
        setError(msg || "No data returned");
        return;
      }
      setData(json.data);
    } catch (e) {
      setError(formatNetworkError(e));
    } finally {
      setLoading(false);
    }
  };

  const runOptimize = async () => {
    setLoadingOptimize(true);
    setOptimizeError(null);
    setOptimizeResult(null);
    try {
      const params = new URLSearchParams({
        symbol: symbol.trim() || "BTC-USD",
        period: period.trim() || "730d",
        interval: interval.trim() || "1h",
        n_trials: "20",
        metric: "total_return",
      });
      const res = await fetch(`/api/analysis/strategy-optimize?${params}`);
      const json = await res.json();
      if (!res.ok) {
        setOptimizeError([json.error, json.details].filter(Boolean).join(" — ") || "Optimization failed");
        return;
      }
      if (!json.success || !json.data) {
        setOptimizeError("No optimization result returned");
        return;
      }
      setOptimizeResult(json.data);
    } catch (e) {
      setOptimizeError(formatNetworkError(e));
    } finally {
      setLoadingOptimize(false);
    }
  };

  const applyOptimizedParams = () => {
    if (!optimizeResult?.best_params) return;
    const p = optimizeResult.best_params;
    if (p.n_components != null) setNComponents(p.n_components);
    if (p.cooldown_hours != null) setAppliedCooldownHours(p.cooldown_hours);
    if (p.leverage != null) setAppliedLeverage(p.leverage);
    if (p.min_confirmations != null) setAppliedMinConfirmations(p.min_confirmations);
    setData(null);
    setError(null);
    setTimeout(() => runBacktestWithParams(p), 0);
  };

  const runBacktestWithParams = async (overrides: OptimizeResult["best_params"]) => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const params = new URLSearchParams({
        symbol: symbol.trim() || "BTC-USD",
        period: period.trim() || "730d",
        interval: interval.trim() || "1h",
        n_components: String(overrides.n_components ?? nComponents),
      });
      if (overrides.cooldown_hours != null) params.set("cooldown_hours", String(overrides.cooldown_hours));
      if (overrides.leverage != null) params.set("leverage", String(overrides.leverage));
      if (overrides.min_confirmations != null) params.set("min_confirmations", String(overrides.min_confirmations));
      if (allowShort) params.set("allow_short", "true");
      if (allowShort && appliedMinBearConfirmations != null) params.set("min_bear_confirmations", String(appliedMinBearConfirmations));
      const res = await fetch(`/api/analysis/hmm-regime-backtest?${params}`);
      const json = await res.json();
      if (!res.ok) {
        setError([json.error, json.details].filter(Boolean).join(" — ") || "Request failed");
        return;
      }
      if (!json.success || !json.data) {
        setError("No data returned");
        return;
      }
      setData(json.data);
    } catch (e) {
      setError(formatNetworkError(e));
    } finally {
      setLoading(false);
    }
  };

  const clearAppliedParams = () => {
    setAppliedCooldownHours(null);
    setAppliedLeverage(null);
    setAppliedMinConfirmations(null);
    setAppliedMinBearConfirmations(null);
  };

  const runWalkForward = async () => {
    setLoadingWalkForward(true);
    setWalkForwardError(null);
    setWalkForwardData(null);
    try {
      const params = new URLSearchParams({
        symbol: symbol.trim() || "BTC-USD",
        period: period.trim() || "365d",
        interval: interval.trim() || "1h",
        n_folds: "4",
        n_components: String(nComponents),
      });
      const res = await fetch(`/api/analysis/walk-forward?${params}`);
      const json = await res.json();
      if (!res.ok) {
        setWalkForwardError([json.error, json.details].filter(Boolean).join(" — ") || "Walk-forward failed");
        return;
      }
      if (!json.success || !json.data) {
        setWalkForwardError("No walk-forward result returned");
        return;
      }
      setWalkForwardData(json.data);
    } catch (e) {
      setWalkForwardError(formatNetworkError(e));
    } finally {
      setLoadingWalkForward(false);
    }
  };

  const chartData = data
    ? (() => {
        const n = Math.min(LAST_N, data.timestamps.length);
        const from = data.timestamps.length - n;
        const equityCurve = data.equity_curve ?? [];
        const startingCapital = 10_000;
        return data.timestamps.slice(from).map((t, i) => {
          const j = from + i;
          const state = data.states?.[j];
          const isBull = state === data.bull_state_id;
          const rawEquity = equityCurve[j];
          const equity =
            typeof rawEquity === "number" && Number.isFinite(rawEquity)
              ? rawEquity
              : typeof equityCurve[j - 1] === "number"
                ? equityCurve[j - 1]
                : startingCapital;
          return {
            time: t,
            label: new Date(t).toLocaleString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
            }),
            close: data.close[j],
            equity,
            state,
            fill: isBull ? BULL_COLOR : BEAR_COLOR,
          };
        });
      })()
    : [];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Backtest parameters</CardTitle>
          <p className="text-sm text-muted-foreground">
            HMM Regime + 8 confirmations (7/8), 48h cooldown, 1.25x leverage.
            $10,000 starting capital.
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="space-y-2">
            <Label htmlFor="bt-symbol">Symbol</Label>
            <Input
              id="bt-symbol"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="BTC-USD"
              className="w-32"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="bt-period">Period</Label>
            <Input
              id="bt-period"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              placeholder="730d"
              className="w-24"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="bt-interval">Interval</Label>
            <Input
              id="bt-interval"
              value={interval}
              onChange={(e) => setInterval(e.target.value)}
              placeholder="1h"
              className="w-20"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="bt-n">HMM states</Label>
            <Input
              id="bt-n"
              type="number"
              min={2}
              max={15}
              value={nComponents}
              onChange={(e) => setNComponents(Number(e.target.value) || 7)}
              className="w-20"
            />
          </div>
          <div className="flex items-center gap-2 space-y-2">
            <input
              id="bt-allow-short"
              type="checkbox"
              checked={allowShort}
              onChange={(e) => setAllowShort(e.target.checked)}
              className="h-4 w-4 rounded border-input"
            />
            <Label htmlFor="bt-allow-short" className="cursor-pointer font-normal">
              Include short trades
            </Label>
          </div>
          {allowShort && (
            <div className="space-y-2">
              <Label htmlFor="bt-min-bear">Min bear confirmations</Label>
              <Input
                id="bt-min-bear"
                type="number"
                min={1}
                max={8}
                placeholder={appliedMinConfirmations != null ? String(appliedMinConfirmations) : "7"}
                value={appliedMinBearConfirmations ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  setAppliedMinBearConfirmations(v === "" ? null : Number(v));
                }}
                className="w-24"
              />
            </div>
          )}
          <Button onClick={runBacktest} disabled={loading}>
            {loading ? "Running…" : "Run Backtest"}
          </Button>
          <Button
            variant="outline"
            onClick={runOptimize}
            disabled={loadingOptimize}
          >
            {loadingOptimize ? "Optimizing…" : "Optimize strategy"}
          </Button>
          <Button
            variant="outline"
            onClick={runWalkForward}
            disabled={loadingWalkForward}
          >
            {loadingWalkForward ? "Running…" : "Validate (walk-forward)"}
          </Button>
        </CardContent>
      </Card>

      {walkForwardError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {walkForwardError}
        </div>
      )}

      {(appliedCooldownHours != null || appliedLeverage != null || appliedMinConfirmations != null || allowShort || appliedMinBearConfirmations != null) && (
        <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span>Applied params:</span>
          {appliedCooldownHours != null && <Badge variant="secondary">cooldown {appliedCooldownHours}h</Badge>}
          {appliedLeverage != null && <Badge variant="secondary">leverage {appliedLeverage}</Badge>}
          {appliedMinConfirmations != null && <Badge variant="secondary">min confirm {appliedMinConfirmations}</Badge>}
          {allowShort && <Badge variant="secondary">short on</Badge>}
          {allowShort && appliedMinBearConfirmations != null && <Badge variant="secondary">min bear {appliedMinBearConfirmations}</Badge>}
          <Button variant="ghost" size="sm" onClick={clearAppliedParams}>
            Clear
          </Button>
        </div>
      )}

      {optimizeError && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {optimizeError}
        </div>
      )}

      {walkForwardData && (
        <Card>
          <CardHeader>
            <CardTitle>Walk-forward validation</CardTitle>
            <p className="text-sm text-muted-foreground">
              Mean return {walkForwardData.mean_return_pct.toFixed(2)}% (std {walkForwardData.std_return_pct.toFixed(2)}%) over {walkForwardData.n_folds} folds. Strategy beat buy-and-hold in {walkForwardData.wins_vs_bh}/{walkForwardData.n_folds} folds.
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-4">
              <div>
                <p className="text-xs text-muted-foreground">Mean return %</p>
                <p className="tabular-nums">{walkForwardData.mean_return_pct.toFixed(2)}%</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Mean alpha %</p>
                <p className="tabular-nums">{walkForwardData.mean_alpha_pct.toFixed(2)}%</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Wins vs B&amp;H</p>
                <p className="tabular-nums">{walkForwardData.wins_vs_bh} / {walkForwardData.n_folds}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Min / Max return %</p>
                <p className="tabular-nums">{walkForwardData.min_return_pct.toFixed(2)}% / {walkForwardData.max_return_pct.toFixed(2)}%</p>
              </div>
            </div>
            {walkForwardData.folds?.length > 0 && (
              <div className="rounded-md border overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/50">
                      <th className="text-left p-2">Fold</th>
                      <th className="text-left p-2">Test period</th>
                      <th className="text-right p-2">Return %</th>
                      <th className="text-right p-2">B&amp;H %</th>
                      <th className="text-right p-2">Alpha %</th>
                      <th className="text-right p-2">Trades</th>
                    </tr>
                  </thead>
                  <tbody>
                    {walkForwardData.folds.map((f: { fold: number; test_start: string; test_end: string; total_return_pct: number; buy_hold_return_pct: number; alpha_pct: number; n_trades: number }) => (
                      <tr key={f.fold} className="border-b last:border-0">
                        <td className="p-2">{f.fold}</td>
                        <td className="p-2 text-muted-foreground">{f.test_start.slice(0, 10)} – {f.test_end.slice(0, 10)}</td>
                        <td className="text-right p-2 tabular-nums">{f.total_return_pct.toFixed(2)}%</td>
                        <td className="text-right p-2 tabular-nums">{f.buy_hold_return_pct.toFixed(2)}%</td>
                        <td className="text-right p-2 tabular-nums">{f.alpha_pct.toFixed(2)}%</td>
                        <td className="text-right p-2 tabular-nums">{f.n_trades}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {optimizeResult && (
        <Card>
          <CardHeader>
            <CardTitle>Strategy optimization</CardTitle>
            <p className="text-sm text-muted-foreground">
              {optimizeResult.n_completed_ok === 0 ? (
                "All trials failed (e.g. data fetch). Try again or check symbol/period."
              ) : (
                <>Best metric: {optimizeResult.best_value != null ? optimizeResult.best_value.toFixed(2) : "—"} ({optimizeResult.metric}) over {optimizeResult.n_trials} trials{optimizeResult.n_completed_ok != null ? ` (${optimizeResult.n_completed_ok} ok)` : ""}.</>
              )}
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium mb-1">Best params</p>
              <div className="flex flex-wrap gap-2">
                {optimizeResult.best_params.n_components != null && (
                  <Badge variant="outline">n_components: {optimizeResult.best_params.n_components}</Badge>
                )}
                {optimizeResult.best_params.cooldown_hours != null && (
                  <Badge variant="outline">cooldown_hours: {optimizeResult.best_params.cooldown_hours}</Badge>
                )}
                {optimizeResult.best_params.leverage != null && (
                  <Badge variant="outline">leverage: {optimizeResult.best_params.leverage}</Badge>
                )}
                {optimizeResult.best_params.min_confirmations != null && (
                  <Badge variant="outline">min_confirmations: {optimizeResult.best_params.min_confirmations}</Badge>
                )}
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={applyOptimizedParams} disabled={loading}>
                Apply and run backtest
              </Button>
            </div>
            {optimizeResult.trials_summary?.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">Top trials</p>
                <div className="rounded-md border overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/50">
                        <th className="text-left p-2">Trial</th>
                        <th className="text-right p-2">Value</th>
                        <th className="text-left p-2">Params</th>
                      </tr>
                    </thead>
                    <tbody>
                      {optimizeResult.trials_summary.map((t) => (
                        <tr key={t.number} className="border-b last:border-0">
                          <td className="p-2">{t.number}</td>
                          <td className="text-right p-2 tabular-nums">{t.value != null ? t.value.toFixed(2) : "—"}</td>
                          <td className="p-2 text-muted-foreground">
                            {JSON.stringify(t.params)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

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
                <CardTitle className="text-base">Current signal</CardTitle>
              </CardHeader>
              <CardContent>
                <Badge
                  variant={data.current_signal === "Long" ? "default" : data.current_signal === "Short" ? "destructive" : "secondary"}
                  className={
                    data.current_signal === "Long"
                      ? "bg-green-600 hover:bg-green-700"
                      : data.current_signal === "Short"
                        ? "bg-red-600 hover:bg-red-700"
                        : ""
                  }
                >
                  {data.current_signal}
                </Badge>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Current regime</CardTitle>
              </CardHeader>
              <CardContent>
                <Badge
                  style={{
                    backgroundColor:
                      data.current_regime === "Bull"
                        ? BULL_COLOR + "30"
                        : BEAR_COLOR + "30",
                    color: data.current_regime === "Bull" ? BULL_COLOR : BEAR_COLOR,
                    borderColor:
                      data.current_regime === "Bull" ? BULL_COLOR : BEAR_COLOR,
                  }}
                >
                  {data.current_regime}
                </Badge>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Total return
                </CardTitle>
              </CardHeader>
              <CardContent>
                <span
                  className={
                    data.total_return_pct >= 0
                      ? "text-green-600"
                      : "text-destructive"
                  }
                >
                  {data.total_return_pct >= 0 ? "+" : ""}
                  {data.total_return_pct.toFixed(2)}%
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Alpha vs Buy & Hold
                </CardTitle>
              </CardHeader>
              <CardContent>
                <span
                  className={
                    data.alpha_pct >= 0 ? "text-green-600" : "text-destructive"
                  }
                >
                  {data.alpha_pct >= 0 ? "+" : ""}
                  {data.alpha_pct.toFixed(2)}%
                </span>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Win rate</CardTitle>
              </CardHeader>
              <CardContent>
                <span className="tabular-nums">
                  {data.win_rate.toFixed(1)}%
                </span>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {data.trades.some((t) => t.side === "short")
                    ? `${data.trades.filter((t) => t.side !== "short").length} long, ${data.trades.filter((t) => t.side === "short").length} short`
                    : `${data.trades.length} trades`}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  Max drawdown
                </CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-destructive tabular-nums">
                  -{data.max_drawdown_pct.toFixed(2)}%
                </span>
              </CardContent>
            </Card>
          </div>

          {chartData.length > 0 && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle>Price by regime (last {chartData.length} bars)</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Green = Bull, Red = Bear. Close price.
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
                          yAxisId="price"
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
                                <div>
                                  Close:{" "}
                                  {typeof p.close === "number"
                                    ? p.close.toFixed(2)
                                    : p.close}
                                </div>
                                <div>
                                  Regime:{" "}
                                  {p.state === data.bull_state_id ? "Bull" : "Bear"}
                                </div>
                              </div>
                            );
                          }}
                        />
                        <Line
                          yAxisId="price"
                          type="monotone"
                          dataKey="close"
                          stroke="hsl(var(--muted-foreground))"
                          strokeWidth={1}
                          dot={(props) => {
                            const { cx, cy, payload } = props;
                            if (cx == null || cy == null) return null;
                            return (
                              <circle
                                cx={cx}
                                cy={cy}
                                r={2.5}
                                fill={payload?.fill ?? "#888"}
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

              <Card>
                <CardHeader>
                  <CardTitle>Equity curve</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Strategy equity ($10k start, 1.25x leverage on PnL).
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="h-[240px] w-full">
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
                          domain={[0, "auto"]}
                          tick={{ fontSize: 10 }}
                          tickFormatter={(v) =>
                            typeof v === "number" && v >= 1000
                              ? `$${(v / 1000).toFixed(1)}k`
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
                                <div>
                                  Equity: $
                                  {typeof p.equity === "number"
                                    ? p.equity.toFixed(2)
                                    : p.equity}
                                </div>
                              </div>
                            );
                          }}
                        />
                        <Line
                          type="monotone"
                          dataKey="equity"
                          stroke="hsl(var(--primary))"
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                          connectNulls={true}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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

type MultivariateData = {
  current_signal: string;
  current_asset: string | null;
  current_asset_label: string | null;
  assets: Array<{ symbol: string; label: string }>;
  timestamps: string[];
  equity_curve: number[];
  trades: Array<{
    asset: string;
    label: string;
    entry_time: string;
    exit_time: string;
    entry_price: number;
    exit_price: number;
    return_pct: number;
    leveraged_return_pct: number;
  }>;
  total_return_pct: number;
  buy_hold_return_pct: number;
  alpha_pct: number;
  win_rate: number;
  max_drawdown_pct: number;
};

const LAST_N = 500;

export default function MultivariatePage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MultivariateData | null>(null);

  const runBacktest = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/analysis/multivariate-backtest");
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

  useEffect(() => {
    runBacktest();
  }, []);

  const STARTING_CAPITAL = 10_000;
  const chartData =
    data?.timestamps && data?.equity_curve
      ? (() => {
          const n = Math.min(LAST_N, data.timestamps.length);
          const from = data.timestamps.length - n;
          const equityCurve = data.equity_curve;
          return data.timestamps.slice(from).map((t, i) => {
            const j = from + i;
            const rawEquity = equityCurve[j];
            const equity =
              typeof rawEquity === "number" && Number.isFinite(rawEquity)
                ? rawEquity
                : typeof equityCurve[j - 1] === "number" &&
                    Number.isFinite(equityCurve[j - 1])
                  ? equityCurve[j - 1]
                  : STARTING_CAPITAL;
            return {
              time: t,
              label: new Date(t).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                year: "2-digit",
              }),
              equity,
            };
          });
        })()
      : [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Multivariate Multi-Asset (Best Trade at a Time)
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Scores BTC, GOLD (and any configured assets) each bar; holds at most one
          long. Regime + 8 confirmations (7/8), 2-day cooldown, 1.25x leverage.
          Add assets in multivariate_config.py.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Run backtest</CardTitle>
          <p className="text-sm text-muted-foreground">
            Uses default assets from config (e.g. BTC, GOLD). Daily data, equal-weight
            buy-and-hold benchmark.
          </p>
        </CardHeader>
        <CardContent>
          <Button onClick={runBacktest} disabled={loading}>
            {loading ? "Running…" : "Refresh backtest"}
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
                <CardTitle className="text-base">Current signal</CardTitle>
              </CardHeader>
              <CardContent>
                <Badge
                  variant={data.current_signal === "Long" ? "default" : "secondary"}
                  className={
                    data.current_signal === "Long"
                      ? "bg-green-600 hover:bg-green-700"
                      : ""
                  }
                >
                  {data.current_signal}
                  {data.current_asset_label
                    ? ` ${data.current_asset_label}`
                    : ""}
                </Badge>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Assets in universe</CardTitle>
              </CardHeader>
              <CardContent>
                <span className="text-sm text-muted-foreground">
                  {data.assets.map((a) => a.label).join(", ")}
                </span>
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
                  Alpha vs equal-weight buy & hold
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
                  {data.trades.length} trades
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
            <Card>
              <CardHeader>
                <CardTitle>Equity curve</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Strategy equity ($10k start, 1.25x leverage). Last {chartData.length} bars.
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-[280px] w-full">
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
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}

          {data.trades.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Trades</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Asset, entry/exit, return. One position at a time; rotation when another asset scores higher.
                </p>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-2 font-medium">Asset</th>
                        <th className="text-left py-2 font-medium">Entry</th>
                        <th className="text-left py-2 font-medium">Exit</th>
                        <th className="text-right py-2 font-medium">Entry $</th>
                        <th className="text-right py-2 font-medium">Exit $</th>
                        <th className="text-right py-2 font-medium">Return %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.trades.map((t, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-2">{t.label}</td>
                          <td className="py-2 text-muted-foreground">
                            {new Date(t.entry_time).toLocaleDateString()}
                          </td>
                          <td className="py-2 text-muted-foreground">
                            {new Date(t.exit_time).toLocaleDateString()}
                          </td>
                          <td className="py-2 text-right tabular-nums">
                            {t.entry_price.toFixed(2)}
                          </td>
                          <td className="py-2 text-right tabular-nums">
                            {t.exit_price.toFixed(2)}
                          </td>
                          <td
                            className={`py-2 text-right tabular-nums ${
                              t.return_pct >= 0 ? "text-green-600" : "text-destructive"
                            }`}
                          >
                            {t.return_pct >= 0 ? "+" : ""}
                            {t.return_pct.toFixed(2)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

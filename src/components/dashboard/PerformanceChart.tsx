"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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

type Snapshot = {
  date: string;
  totalValue: number;
  cashBalance: number;
  investedValue: number;
  unrealizedPL: number;
  realizedPL: number;
};

function formatPkr(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(0)}K`;
  return n.toFixed(0);
}

type MwrPeriod = "30d" | "90d" | "1y";

export function PerformanceChart() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [summary, setSummary] = useState<{ periodReturn?: number; currentValue?: number } | null>(null);
  const [mwr, setMwr] = useState<Partial<Record<MwrPeriod, number>>>({});
  const [mwrLoading, setMwrLoading] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/portfolio/snapshots?limit=90")
      .then((r) => r.json())
      .then((res) => {
        if (cancelled) return;
        if (res.success && res.data) {
          const list = (res.data.snapshots ?? []).map((s: { date: string; totalValue: number; cashBalance: number; investedValue: number; unrealizedPL: number; realizedPL: number }) => ({
            date: new Date(s.date).toLocaleDateString("en-PK", { month: "short", day: "numeric", year: "2-digit" }),
            totalValue: s.totalValue,
            cashBalance: s.cashBalance,
            investedValue: s.investedValue,
            unrealizedPL: s.unrealizedPL,
            realizedPL: s.realizedPL,
          }));
          setSnapshots(list.reverse());
          if (res.data.summary) {
            setSummary({
              periodReturn: res.data.summary.periodReturn,
              currentValue: res.data.summary.currentValue,
            });
          }
        } else {
          setError(res.error ?? "Failed to load");
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e.message ?? "Request failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const periods: MwrPeriod[] = ["30d", "90d", "1y"];
    Promise.all(
      periods.map((period) =>
        fetch(`/api/portfolio/returns?period=${period}`).then((r) => r.json())
      )
    ).then((responses) => {
      if (cancelled) return;
      const next: Partial<Record<MwrPeriod, number>> = {};
      responses.forEach((res, i) => {
        const period = periods[i];
        if (res.success && res.data?.moneyWeightedReturnPct != null) {
          next[period] = res.data.moneyWeightedReturnPct;
        }
      });
      setMwr(next);
    }).finally(() => {
      if (!cancelled) setMwrLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Portfolio value over time</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-80 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6 text-destructive">{error}</CardContent>
      </Card>
    );
  }

  const periods: { key: MwrPeriod; label: string }[] = [
    { key: "30d", label: "30 days" },
    { key: "90d", label: "90 days" },
    { key: "1y", label: "1 year" },
  ];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Money-weighted return
          </CardTitle>
          <p className="text-xs text-muted-foreground">
            Modified Dietz (accounts for deposits/withdrawals)
          </p>
        </CardHeader>
        <CardContent>
          {mwrLoading ? (
            <div className="grid gap-4 grid-cols-3">
              {periods.map((p) => (
                <Skeleton key={p.key} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              {periods.map(({ key, label }) => {
                const value = mwr[key];
                const isNum = typeof value === "number";
                return (
                  <div key={key} className="rounded-lg border bg-muted/40 p-3">
                    <p className="text-xs text-muted-foreground">{label}</p>
                    <p className={`text-xl font-semibold ${isNum && value >= 0 ? "text-green-600 dark:text-green-400" : isNum ? "text-red-600 dark:text-red-400" : ""}`}>
                      {isNum ? `${value >= 0 ? "+" : ""}${value.toFixed(2)}%` : "—"}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
      {summary && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Current value
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-semibold">
                Rs {summary.currentValue != null ? formatPkr(summary.currentValue) : "-"}
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Period return
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className={`text-2xl font-semibold ${(summary.periodReturn ?? 0) >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
                {summary.periodReturn != null ? `${summary.periodReturn >= 0 ? "+" : ""}${summary.periodReturn.toFixed(2)}%` : "-"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}
      <Card>
        <CardHeader>
          <CardTitle>Portfolio value over time</CardTitle>
          <p className="text-sm text-muted-foreground">
            From AccountSnapshot history
          </p>
        </CardHeader>
        <CardContent>
          {snapshots.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              No snapshot history. Record account snapshots to see performance.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={snapshots} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => formatPkr(Number(v))} />
                <Tooltip formatter={(v) => [formatPkr(Number(v ?? 0)), "Value"]} labelFormatter={(l) => String(l ?? "")} />
                <Line type="monotone" dataKey="totalValue" stroke="hsl(var(--primary))" strokeWidth={2} dot={false} name="Total value" />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

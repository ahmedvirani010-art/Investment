"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

type Summary = {
  totalValue: number;
  totalCost: number;
  totalUnrealizedPL: number;
  totalUnrealizedPLPercent: number;
  totalRealizedGain: number;
  totalDividends: number;
  totalReturnUnrealized: number;
  totalReturnPercent: number;
  numberOfPositions: number;
};

function formatPkr(n: number): string {
  return new Intl.NumberFormat("en-PK", {
    style: "decimal",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

function formatPct(n: number): string {
  const s = n >= 0 ? `+${n.toFixed(2)}` : n.toFixed(2);
  return `${s}%`;
}

export function PortfolioMetrics() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/portfolio/holdings")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        if (data.success && data.data?.summary) {
          setSummary(data.data.summary);
        } else {
          setError(data.error ?? "Failed to load");
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

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6 text-destructive">
          {error}
        </CardContent>
      </Card>
    );
  }

  if (!summary) {
    return (
      <Card>
        <CardContent className="py-6 text-muted-foreground">
          No portfolio data. Add holdings to see metrics.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total Value
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-semibold">
            Rs {formatPkr(summary.totalValue)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {summary.numberOfPositions} positions
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total Cost
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-semibold">
            Rs {formatPkr(summary.totalCost)}
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Unrealized P&L
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p
            className={`text-2xl font-semibold ${
              summary.totalUnrealizedPL >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
            }`}
          >
            Rs {formatPkr(summary.totalUnrealizedPL)} ({formatPct(summary.totalUnrealizedPLPercent)})
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Realized + Dividends
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-semibold">
            Rs {formatPkr(summary.totalRealizedGain + summary.totalDividends)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Total return {formatPct(summary.totalReturnPercent)}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

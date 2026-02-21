"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

type Holding = {
  id: string;
  symbol: string;
  name: string;
  sector: string;
  quantity: number;
  averageCost: number;
  currentPrice: number;
  totalCost: number;
  currentValue: number;
  unrealizedPL: number;
  unrealizedPLPercent: number;
};

type RiskSummary = {
  accountValue: number;
  totalEquity: number;
  diversificationScore: number;
  sectorExposure: { sector: string; value: number; pct: number }[];
  violations: { type: string; message: string; value?: number }[];
};

function formatPkr(n: number): string {
  return new Intl.NumberFormat("en-PK", {
    style: "decimal",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(n);
}

function formatPct(n: number): string {
  const s = n >= 0 ? `+${n.toFixed(2)}` : n.toFixed(2);
  return `${s}%`;
}

export function StockPositionCard({ ticker }: { ticker: string }) {
  const [loading, setLoading] = useState(true);
  const [holding, setHolding] = useState<Holding | null>(null);
  const [riskSummary, setRiskSummary] = useState<RiskSummary | null>(null);

  useEffect(() => {
    setLoading(true);
    setHolding(null);
    setRiskSummary(null);
    Promise.all([
      fetch("/api/portfolio/holdings").then((r) => r.json()),
      fetch("/api/analysis/risk-metrics").then((r) => r.json()),
    ])
      .then(([holdingsRes, riskRes]) => {
        if (holdingsRes.success && holdingsRes.data?.holdings) {
          const h = (holdingsRes.data.holdings as Holding[]).find(
            (x) => x.symbol.toUpperCase() === ticker.toUpperCase()
          );
          setHolding(h ?? null);
        }
        if (riskRes.success && riskRes.data?.summary) {
          setRiskSummary(riskRes.data.summary as RiskSummary);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [ticker]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Position & Risk</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
        </CardContent>
      </Card>
    );
  }

  const sectorExposure = riskSummary?.sectorExposure?.find(
    (s) => holding && s.sector === holding.sector
  );
  const violationsForSymbol = riskSummary?.violations?.filter(
    (v) => v.message.includes(ticker) || (holding && v.message.includes(holding.sector))
  ) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Position & Risk</CardTitle>
        <p className="text-sm text-muted-foreground">
          Your position in this stock and risk context
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {holding ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Position</span>
              <span className="font-medium">{holding.quantity} shares</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Avg cost</span>
              <span className="tabular-nums">₨ {formatPkr(holding.averageCost)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Current value</span>
              <span className="tabular-nums">₨ {formatPkr(holding.currentValue)}</span>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Unrealized P&L</span>
              <span
                className={
                  holding.unrealizedPL >= 0
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }
              >
                {formatPkr(holding.unrealizedPL)} ({formatPct(holding.unrealizedPLPercent)})
              </span>
            </div>
            {sectorExposure != null && (
              <div className="flex items-center justify-between text-sm pt-2 border-t border-border">
                <span className="text-muted-foreground">Sector exposure ({holding.sector})</span>
                <span className="tabular-nums">{sectorExposure.pct.toFixed(1)}%</span>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">You don’t hold a position in this stock.</p>
        )}

        {violationsForSymbol.length > 0 && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm">
            <p className="font-medium text-amber-700 dark:text-amber-400 mb-1">Warnings</p>
            <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
              {violationsForSymbol.map((v, i) => (
                <li key={i}>{v.message}</li>
              ))}
            </ul>
          </div>
        )}

        <Button variant="outline" size="sm" asChild>
          <Link href="/dashboard/risk">Full risk & position sizer</Link>
        </Button>
      </CardContent>
    </Card>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type SectorExposure = { sector: string; value: number; pct: number };
type Violation = { type: string; message: string; value?: number };
type Settings = {
  maxRiskPerTradePct: number;
  maxPositionSizePct: number;
  maxTotalRiskPct: number;
  maxSectorExposurePct: number;
  maxSinglePositionPct: number;
  minPositions: number;
  maxPositions: number;
  defaultStopLossPct: number;
  minRewardRiskRatio: number;
};

type Summary = {
  accountValue: number;
  totalEquity: number;
  totalRiskPct: number;
  diversificationScore: number;
  sectorExposure: SectorExposure[];
  violations: Violation[];
  settings: Settings;
};

function formatPkr(n: number): string {
  return new Intl.NumberFormat("en-PK", {
    style: "decimal",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(n);
}

export function RiskSummary() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [positionsCount, setPositionsCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/analysis/risk-metrics")
      .then((r) => r.json())
      .then((res) => {
        if (cancelled) return;
        if (res.success && res.data) {
          setSummary(res.data.summary);
          setPositionsCount(res.data.positionsCount ?? 0);
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

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
        <Skeleton className="h-32" />
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-6 text-destructive">{error}</CardContent>
      </Card>
    );
  }

  if (!summary) {
    return (
      <Card>
        <CardContent className="py-6 text-muted-foreground">
          No risk settings or portfolio data.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Account / Equity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-semibold">Rs {formatPkr(summary.accountValue)}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {positionsCount} positions
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Diversification score
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-semibold">{summary.diversificationScore}%</p>
            <p className="text-xs text-muted-foreground mt-1">
              Target: {summary.settings.minPositions}–{summary.settings.maxPositions} positions
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Max sector exposure
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-semibold">{summary.settings.maxSectorExposurePct}%</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Violations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className={`text-xl font-semibold ${summary.violations.length > 0 ? "text-destructive" : "text-green-600 dark:text-green-400"}`}>
              {summary.violations.length}
            </p>
          </CardContent>
        </Card>
      </div>

      {summary.sectorExposure.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Sector exposure</CardTitle>
            <p className="text-sm text-muted-foreground">
              Limit: {summary.settings.maxSectorExposurePct}% per sector
            </p>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {summary.sectorExposure.map((s) => (
                <div key={s.sector} className="flex items-center justify-between gap-4">
                  <span className="font-medium">{s.sector}</span>
                  <span className="text-muted-foreground">
                    Rs {formatPkr(s.value)} ({s.pct}%)
                  </span>
                  {s.pct > summary.settings.maxSectorExposurePct ? (
                    <Badge variant="destructive">Over limit</Badge>
                  ) : null}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {summary.violations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Risk violations</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc list-inside space-y-1 text-sm">
              {summary.violations.map((v, i) => (
                <li key={i} className="text-destructive">
                  {v.message}
                  {v.value != null && ` (${v.value.toFixed(1)}%)`}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Risk settings</CardTitle>
          <p className="text-sm text-muted-foreground">
            From RiskSettings model
          </p>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm">
          <div className="grid grid-cols-2 gap-2">
            <span className="text-muted-foreground">Max risk per trade</span>
            <span>{summary.settings.maxRiskPerTradePct}%</span>
            <span className="text-muted-foreground">Max position size</span>
            <span>{summary.settings.maxPositionSizePct}%</span>
            <span className="text-muted-foreground">Max total risk</span>
            <span>{summary.settings.maxTotalRiskPct}%</span>
            <span className="text-muted-foreground">Max single position</span>
            <span>{summary.settings.maxSinglePositionPct}%</span>
            <span className="text-muted-foreground">Default stop loss</span>
            <span>{summary.settings.defaultStopLossPct}%</span>
            <span className="text-muted-foreground">Min reward/risk ratio</span>
            <span>{summary.settings.minRewardRiskRatio}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

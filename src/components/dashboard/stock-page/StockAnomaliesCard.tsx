"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type Anomaly = {
  symbol: string;
  date: string;
  type: string;
  severity: string;
  value: number;
  baseline: number;
  z_score: number;
  description: string;
};

const severityStyle: Record<string, string> = {
  HIGH: "bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30",
  MEDIUM: "bg-amber-500/20 text-amber-700 dark:text-amber-400 border-amber-500/30",
  LOW: "bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30",
};

export function StockAnomaliesCard({ ticker }: { ticker: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setAnomalies([]);
    const params = new URLSearchParams({
      lookback_days: "60",
      z_threshold: "2.5",
      symbols: ticker,
    });
    fetch(`/api/analysis/anomalies?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.anomalies) {
          const list = res.data.anomalies as Anomaly[];
          setAnomalies(list.filter((a) => a.symbol === ticker));
        } else {
          setError(res.error ?? "Failed to load anomalies");
        }
      })
      .catch((e) => {
        setError(e.message ?? "Request failed");
      })
      .finally(() => setLoading(false));
  }, [ticker]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Anomalies</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle>Anomalies</CardTitle>
        </CardHeader>
        <CardContent className="text-destructive">{error}</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Anomalies</CardTitle>
        <p className="text-sm text-muted-foreground">Last 60 days, z-score ≥ 2.5</p>
      </CardHeader>
      <CardContent>
        {anomalies.length === 0 ? (
          <p className="text-sm text-muted-foreground">No anomalies detected for this symbol.</p>
        ) : (
          <ul className="space-y-2">
            {anomalies.map((a, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2 text-sm border-b border-border pb-2 last:border-0">
                <Badge className={severityStyle[a.severity] ?? "bg-muted"}>{a.severity}</Badge>
                <span>{a.type}</span>
                <span className="text-muted-foreground">{a.date}</span>
                <span className="font-mono tabular-nums">{a.description || `z=${a.z_score.toFixed(2)}`}</span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

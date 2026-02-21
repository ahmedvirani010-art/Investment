"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

export function AnomalyAlert() {
  const [data, setData] = useState<{
    anomalies: Anomaly[];
    summary: {
      total_anomalies: number;
      severity_distribution: Record<string, number>;
      top_anomalous_stocks: string[];
    };
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lookbackDays, setLookbackDays] = useState(60);
  const [zThreshold, setZThreshold] = useState(2.5);
  const [symbols, setSymbols] = useState("");

  const runAnalysis = () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      lookback_days: String(lookbackDays),
      z_threshold: String(zThreshold),
    });
    if (symbols.trim()) params.set("symbols", symbols.trim());
    fetch(`/api/analysis/anomalies?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data) {
          setData({
            anomalies: res.data.anomalies ?? [],
            summary: res.data.summary ?? { total_anomalies: 0, severity_distribution: {}, top_anomalous_stocks: [] },
          });
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
          <CardTitle>Parameters</CardTitle>
          <p className="text-sm text-muted-foreground">
            Anomaly detection (PSXAnomalyAgent). Leave symbols empty for default list.
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="space-y-2">
            <Label>Lookback days</Label>
            <Input
              type="number"
              min={30}
              max={90}
              value={lookbackDays}
              onChange={(e) => setLookbackDays(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <div className="space-y-2">
            <Label>Z-score threshold</Label>
            <Input
              type="number"
              min={2}
              max={4}
              step={0.1}
              value={zThreshold}
              onChange={(e) => setZThreshold(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <div className="space-y-2 min-w-[200px]">
            <Label>Symbols (comma-separated)</Label>
            <Input
              placeholder="e.g. LUCK, PSO, HBL"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
            />
          </div>
          <Button onClick={runAnalysis} disabled={loading}>
            {loading ? "Running..." : "Run anomaly detection"}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <Card>
          <CardContent className="py-4 text-destructive">{error}</CardContent>
        </Card>
      )}

      {loading && (
        <Card>
          <CardContent className="py-8">
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      )}

      {data && !loading && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Summary</CardTitle>
              <p className="text-sm text-muted-foreground">
                Total anomalies: {data.summary.total_anomalies}
                {Object.keys(data.summary.severity_distribution).length > 0 && (
                  <> · Severity: {Object.entries(data.summary.severity_distribution).map(([k, v]) => `${k}: ${v}`).join(", ")}</>
                )}
              </p>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Anomalies</CardTitle>
            </CardHeader>
            <CardContent>
              {data.anomalies.length === 0 ? (
                <p className="text-muted-foreground py-4">No anomalies detected.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Date</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead className="text-right">Z-Score</TableHead>
                      <TableHead>Description</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.anomalies.map((a, i) => (
                      <TableRow key={`${a.symbol}-${a.date}-${i}`}>
                        <TableCell className="font-medium">{a.symbol}</TableCell>
                        <TableCell>{a.date}</TableCell>
                        <TableCell>{a.type}</TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={severityStyle[a.severity] ?? ""}
                          >
                            {a.severity}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">{a.z_score?.toFixed(2) ?? "-"}</TableCell>
                        <TableCell className="max-w-[300px] truncate">{a.description}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {!data && !loading && !error && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            Set parameters and click &quot;Run anomaly detection&quot; to load data.
          </CardContent>
        </Card>
      )}
    </div>
  );
}

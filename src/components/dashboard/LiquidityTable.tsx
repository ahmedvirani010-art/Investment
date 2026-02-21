"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

type LiquidityRow = {
  symbol: string;
  name: string;
  avg_traded_value: number;
  avg_volume: number;
  avg_price: number;
  current_price: number;
  rank: number;
};

function formatPkr(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(2)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(2)}K`;
  return n.toFixed(0);
}

export function LiquidityTable() {
  const [data, setData] = useState<{
    liquidity_analysis: LiquidityRow[];
    summary: {
      total_stocks: number;
      stocks_screened?: number;
      total_daily_value: number;
      top_stock: LiquidityRow | null;
    };
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lookbackDays, setLookbackDays] = useState(30);
  const [minPrice, setMinPrice] = useState(20);
  const [topN, setTopN] = useState(50);

  const runAnalysis = () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      lookback_days: String(lookbackDays),
      min_price: String(minPrice),
      top_n: String(topN),
    });
    fetch(`/api/analysis/liquidity?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data) {
          setData(res.data);
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
            Configure and run liquidity screening (uses PSXLiquidityScreener)
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="space-y-2">
            <Label>Lookback days</Label>
            <Input
              type="number"
              min={7}
              max={90}
              value={lookbackDays}
              onChange={(e) => setLookbackDays(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <div className="space-y-2">
            <Label>Min price (Rs)</Label>
            <Input
              type="number"
              min={0}
              step={1}
              value={minPrice}
              onChange={(e) => setMinPrice(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <div className="space-y-2">
            <Label>Top N</Label>
            <Input
              type="number"
              min={10}
              max={500}
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              className="w-28"
            />
          </div>
          <Button onClick={runAnalysis} disabled={loading}>
            {loading ? "Running..." : "Run liquidity screen"}
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
        <Card>
          <CardHeader>
            <CardTitle>Top liquid stocks</CardTitle>
            <p className="text-sm text-muted-foreground">
              {typeof data.summary.stocks_screened === "number"
                ? `Screened ${data.summary.stocks_screened} stocks · `
                : ""}
              Top {data.summary.total_stocks} · Total daily value Rs {formatPkr(data.summary.total_daily_value)}
            </p>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rank</TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="text-right">Avg traded value</TableHead>
                  <TableHead className="text-right">Avg volume</TableHead>
                  <TableHead className="text-right">Price</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.liquidity_analysis.map((row) => (
                  <TableRow key={row.symbol}>
                    <TableCell>{row.rank}</TableCell>
                    <TableCell className="font-medium">{row.symbol}</TableCell>
                    <TableCell className="max-w-[200px] truncate">{row.name}</TableCell>
                    <TableCell className="text-right">{formatPkr(row.avg_traded_value)}</TableCell>
                    <TableCell className="text-right">{formatPkr(row.avg_volume)}</TableCell>
                    <TableCell className="text-right">Rs {row.current_price?.toFixed(2) ?? "-"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {!data && !loading && !error && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            Set parameters and click &quot;Run liquidity screen&quot; to load data.
          </CardContent>
        </Card>
      )}
    </div>
  );
}

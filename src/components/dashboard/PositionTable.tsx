"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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

export function PositionTable() {
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});

  useEffect(() => {
    let cancelled = false;
    fetch("/api/portfolio/holdings")
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return;
        if (data.success && data.data?.holdings) {
          setHoldings(data.data.holdings);
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

  // When holdings have price 0, fetch live prices so we can show real Price/Value/P&L
  useEffect(() => {
    const needPrice = holdings.filter((h) => !h.currentPrice || h.currentPrice === 0);
    if (needPrice.length === 0) return;
    const tickers = needPrice.map((h) => h.symbol).join(",");
    let cancelled = false;
    fetch(`/api/price?tickers=${encodeURIComponent(tickers)}`)
      .then((r) => r.json())
      .then((res) => {
        if (cancelled || !res.success || !Array.isArray(res.data)) return;
        const map: Record<string, number> = {};
        for (const row of res.data) {
          if (row?.ticker != null && row?.price != null) {
            map[row.ticker] = Number(row.price);
          }
        }
        setLivePrices((prev) => ({ ...prev, ...map }));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [holdings]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-64 w-full" />
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

  if (holdings.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Positions</CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground py-8 text-center">
          No positions. Add transactions to see holdings.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Positions</CardTitle>
        <p className="text-sm text-muted-foreground">
          Current holdings with cost and P&L
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Symbol</TableHead>
              <TableHead>Name</TableHead>
              <TableHead className="text-right">Qty</TableHead>
              <TableHead className="text-right">Avg Cost</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead className="text-right">Cost</TableHead>
              <TableHead className="text-right">Value</TableHead>
              <TableHead className="text-right">P&L</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {holdings.map((h) => {
              const price = livePrices[h.symbol] ?? h.currentPrice;
              const value = h.quantity * price;
              const pl = value - h.totalCost;
              const plPct = h.totalCost > 0 ? (pl / h.totalCost) * 100 : 0;
              return (
                <TableRow key={h.id}>
                  <TableCell className="font-medium">
                    <Link
                      href={`/dashboard/stock/${h.symbol}`}
                      className="text-primary hover:underline"
                    >
                      {h.symbol}
                    </Link>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate">
                    <Link
                      href={`/dashboard/stock/${h.symbol}`}
                      className="text-foreground hover:underline truncate block"
                    >
                      {h.name}
                    </Link>
                  </TableCell>
                  <TableCell className="text-right">{h.quantity}</TableCell>
                  <TableCell className="text-right">{formatPkr(h.averageCost)}</TableCell>
                  <TableCell className="text-right">{formatPkr(price)}</TableCell>
                  <TableCell className="text-right">{formatPkr(h.totalCost)}</TableCell>
                  <TableCell className="text-right">{formatPkr(value)}</TableCell>
                  <TableCell
                    className={`text-right font-medium ${
                      pl >= 0
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {formatPkr(pl)} ({formatPct(plPct)})
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

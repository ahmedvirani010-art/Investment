"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Holding = {
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

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function PortfolioExport() {
  const [loading, setLoading] = useState(false);

  const exportCsv = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/portfolio/holdings");
      const data = await res.json();
      if (!data.success || !data.data?.holdings) throw new Error("No data");
      const holdings: Holding[] = data.data.holdings;
      const headers = ["Symbol", "Name", "Sector", "Qty", "Avg Cost", "Price", "Cost", "Value", "P&L", "P&L %"];
      const rows = holdings.map((h) => [
        h.symbol,
        `"${(h.name ?? "").replace(/"/g, '""')}"`,
        h.sector,
        h.quantity,
        h.averageCost.toFixed(2),
        h.currentPrice.toFixed(2),
        h.totalCost.toFixed(2),
        h.currentValue.toFixed(2),
        h.unrealizedPL.toFixed(2),
        h.unrealizedPLPercent.toFixed(2),
      ].join(","));
      const csv = [headers.join(","), ...rows].join("\n");
      downloadBlob(new Blob([csv], { type: "text/csv" }), `portfolio-holdings-${new Date().toISOString().slice(0, 10)}.csv`);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const exportJson = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/portfolio/holdings");
      const data = await res.json();
      if (!data.success) throw new Error("No data");
      const json = JSON.stringify(data.data, null, 2);
      downloadBlob(new Blob([json], { type: "application/json" }), `portfolio-holdings-${new Date().toISOString().slice(0, 10)}.json`);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Export</CardTitle>
        <p className="text-sm text-muted-foreground">
          Download current holdings as CSV or JSON
        </p>
      </CardHeader>
      <CardContent className="flex gap-2">
        <Button variant="outline" size="sm" onClick={exportCsv} disabled={loading}>
          Export CSV
        </Button>
        <Button variant="outline" size="sm" onClick={exportJson} disabled={loading}>
          Export JSON
        </Button>
      </CardContent>
    </Card>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
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

type AnnouncementDto = {
  announcement_id: string;
  symbol: string;
  announcement_date: string;
  category?: string | null;
  subcategory?: string | null;
  materiality_tier?: number | null;
  title: string;
  description?: string | null;
  attachment_url?: string | null;
  source_url: string;
  source?: string | null;
  dividend_amount?: number | null;
  dividend_type?: string | null;
  eps?: number | null;
  profit_amount?: number | null;
  profit_change_pct?: number | null;
  revenue?: number | null;
  fetched_date?: string | null;
  is_processed?: boolean;
  market_impact?: string | null;
};

const tierLabels: Record<number, string> = {
  1: "Critical",
  2: "Material",
  3: "Informational",
};

const tierVariant: Record<number, "destructive" | "default" | "secondary" | "outline"> = {
  1: "destructive",
  2: "default",
  3: "secondary",
};

function AnnouncementRow({ a }: { a: AnnouncementDto }) {
  const tier = a.materiality_tier ?? 3;
  return (
    <TableRow>
      <TableCell className="font-medium">{a.symbol}</TableCell>
      <TableCell className="text-muted-foreground text-sm max-w-[200px]">
        {a.announcement_date
          ? new Date(a.announcement_date).toLocaleString(undefined, {
              dateStyle: "short",
              timeStyle: "short",
            })
          : "-"}
      </TableCell>
      <TableCell className="max-w-[320px]">
        <a
          href={a.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline truncate block"
        >
          {a.title || "—"}
        </a>
      </TableCell>
      <TableCell className="text-sm">{a.category ?? "-"}</TableCell>
      <TableCell className="text-sm">{a.subcategory ?? "-"}</TableCell>
      <TableCell>
        <Badge variant={tierVariant[tier] ?? "outline"} className="text-xs">
          {tierLabels[tier] ?? `Tier ${tier}`}
        </Badge>
      </TableCell>
      <TableCell className="text-sm">
        {a.dividend_amount != null && (
          <span>
            {a.dividend_amount}% {a.dividend_type ?? ""}
          </span>
        )}
        {a.profit_change_pct != null && (
          <span className="block text-muted-foreground">
            Profit {a.profit_change_pct > 0 ? "+" : ""}
            {a.profit_change_pct}%
          </span>
        )}
        {a.dividend_amount == null && a.profit_change_pct == null && "-"}
      </TableCell>
    </TableRow>
  );
}

export function AnnouncementsDashboard() {
  const [days, setDays] = useState(7);
  const [symbols, setSymbols] = useState("");
  const [tier, setTier] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [announcements, setAnnouncements] = useState<AnnouncementDto[]>([]);
  const [count, setCount] = useState(0);

  const fetchList = useCallback(() => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      action: "list",
      days: String(days),
    });
    if (symbols.trim()) params.set("symbols", symbols.trim());
    if (tier.trim() && ["1", "2", "3"].includes(tier.trim()))
      params.set("tier", tier.trim());

    fetch(`/api/analysis/announcements?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && Array.isArray(res.announcements)) {
          setAnnouncements(res.announcements);
          setCount(res.count ?? res.announcements.length);
        } else {
          setError(res.error ?? "Failed to load announcements");
          setAnnouncements([]);
          setCount(0);
        }
      })
      .catch((e) => {
        setError(e.message ?? "Request failed");
        setAnnouncements([]);
        setCount(0);
      })
      .finally(() => setLoading(false));
  }, [days, symbols, tier]);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const runSync = () => {
    setSyncing(true);
    setError(null);
    fetch("/api/analysis/announcements?action=sync&days=1")
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          fetchList();
        } else {
          setError(res.error ?? "Sync failed");
        }
      })
      .catch((e) => {
        setError(e.message ?? "Sync request failed");
      })
      .finally(() => setSyncing(false));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <p className="text-sm text-muted-foreground">
            PSX official announcements. List is read from local DB; use Sync to fetch latest from PSX.
          </p>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-4">
          <div className="space-y-2">
            <Label>Lookback (days)</Label>
            <select
              className="flex h-9 w-[120px] rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              <option value={7}>7</option>
              <option value={14}>14</option>
              <option value={30}>30</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label>Symbols (optional)</Label>
            <Input
              placeholder="e.g. HBL, OGDC"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
              className="w-[200px]"
            />
          </div>
          <div className="space-y-2">
            <Label>Tier</Label>
            <select
              className="flex h-9 w-[140px] rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm"
              value={tier}
              onChange={(e) => setTier(e.target.value)}
            >
              <option value="">All</option>
              <option value="1">Critical</option>
              <option value="2">Material</option>
              <option value="3">Informational</option>
            </select>
          </div>
          <Button variant="outline" onClick={fetchList} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </Button>
          <Button onClick={runSync} disabled={syncing}>
            {syncing ? "Syncing…" : "Sync now"}
          </Button>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Announcements ({count})</CardTitle>
          <p className="text-sm text-muted-foreground">
            {!loading && announcements.length > 0
              ? `Showing all ${count} announcement${count !== 1 ? "s" : ""} (complete report).`
              : null}
          </p>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-[200px] w-full" />
          ) : announcements.length === 0 ? (
            <p className="text-muted-foreground py-4">
              No announcements found. Run Sync to fetch from PSX, or run{" "}
              <code className="text-xs bg-muted px-1 rounded">demo_announcement_system.py</code> to seed sample data.
            </p>
          ) : (
            <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Title</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead>Subcategory</TableHead>
                    <TableHead>Tier</TableHead>
                    <TableHead>Key data</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {announcements.map((a) => (
                    <AnnouncementRow key={a.announcement_id} a={a} />
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

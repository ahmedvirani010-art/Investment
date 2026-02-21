"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TradeJournalForm } from "@/components/dashboard/TradeJournalForm";

type Entry = {
  id: string;
  tradePlanId: string;
  symbol: string;
  name: string;
  entryDate: string;
  exitDate: string | null;
  entryPrice: number;
  exitPrice: number | null;
  quantity: number;
  realizedPL: number | null;
  realizedPLPercent: number | null;
  holdingPeriod: number | null;
  strategyLabel: string | null;
  ideaSource: string | null;
  exitMethod: string | null;
  entryNotes: string | null;
  exitNotes: string | null;
  emotionalState: string | null;
  lessonsLearned: string | null;
};

function formatDate(s: string): string {
  try {
    return new Date(s).toLocaleDateString("en-PK");
  } catch {
    return s;
  }
}

export function TradeJournalList() {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingEntry, setEditingEntry] = useState<Entry | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    fetch("/api/portfolio/journal")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.entries) {
          setEntries(res.data.entries);
        } else {
          setError(res.error ?? "Failed to load");
        }
      })
      .catch((e) => setError(e.message ?? "Request failed"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this journal entry? This cannot be undone.")) return;
    setDeletingId(id);
    try {
      const res = await fetch(`/api/portfolio/journal?id=${id}`, { method: "DELETE" });
      const json = await res.json();
      if (json.success) {
        setEntries((prev) => prev.filter((e) => e.id !== id));
      } else {
        alert(json.error ?? "Delete failed");
      }
    } catch {
      alert("Delete failed");
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
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

  // Show edit form inline
  if (editingEntry) {
    return (
      <TradeJournalForm
        entry={editingEntry}
        tradePlanSymbol={editingEntry.symbol}
        onSaved={() => {
          setEditingEntry(null);
          load();
        }}
        onCancel={() => setEditingEntry(null)}
      />
    );
  }

  if (entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trade journal</CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground py-8 text-center">
          No journal entries yet. Close a trade to create one, or add one manually below.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Trade journal</CardTitle>
        <p className="text-sm text-muted-foreground">
          {entries.length} entr{entries.length !== 1 ? "ies" : "y"} · post-trade analysis and lessons learned
        </p>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Symbol</TableHead>
              <TableHead>Entry</TableHead>
              <TableHead>Exit</TableHead>
              <TableHead className="text-right">Entry Px</TableHead>
              <TableHead className="text-right">Exit Px</TableHead>
              <TableHead className="text-right">Qty</TableHead>
              <TableHead className="text-right">P&L</TableHead>
              <TableHead>Strategy</TableHead>
              <TableHead className="w-[120px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.map((e) => (
              <TableRow key={e.id}>
                <TableCell className="font-medium">{e.symbol}</TableCell>
                <TableCell>{formatDate(e.entryDate)}</TableCell>
                <TableCell>{e.exitDate ? formatDate(e.exitDate) : "—"}</TableCell>
                <TableCell className="text-right">{e.entryPrice.toFixed(2)}</TableCell>
                <TableCell className="text-right">
                  {e.exitPrice != null ? e.exitPrice.toFixed(2) : "—"}
                </TableCell>
                <TableCell className="text-right">{e.quantity}</TableCell>
                <TableCell className={`text-right ${(e.realizedPL ?? 0) >= 0 ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}>
                  {e.realizedPL != null ? (
                    <>
                      Rs {e.realizedPL.toLocaleString("en-PK", { maximumFractionDigits: 0 })}
                      {e.realizedPLPercent != null && (
                        <span className="text-xs font-normal text-muted-foreground ml-1">
                          ({e.realizedPLPercent >= 0 ? "+" : ""}{e.realizedPLPercent.toFixed(1)}%)
                        </span>
                      )}
                    </>
                  ) : "—"}
                </TableCell>
                <TableCell className="max-w-[120px] truncate">{e.strategyLabel ?? "—"}</TableCell>
                <TableCell>
                  <div className="flex gap-1 justify-end">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 px-2 text-xs"
                      onClick={() => setEditingEntry(e)}
                    >
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                      disabled={deletingId === e.id}
                      onClick={() => handleDelete(e.id)}
                    >
                      {deletingId === e.id ? "…" : "Del"}
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

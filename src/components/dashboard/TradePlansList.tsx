"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { TradePlanForm } from "@/components/dashboard/TradePlanForm";
import { TradeExecuteDialog, type ExecuteResult } from "@/components/dashboard/TradeExecuteDialog";
import { TradeJournalForm } from "@/components/dashboard/TradeJournalForm";

type Plan = {
  id: string;
  stockId: string;
  symbol: string;
  name: string;
  status: string;
  direction: string;
  entryPrice: number;
  targetPrice: number | null;
  stopLoss: number;
  positionSize: number | null;
  riskAmount: number | null;
  rewardRiskRatio: number | null;
  notes: string | null;
  updatedAt: string;
};

const statusVariant: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  PLANNED: "secondary",
  ACTIVE: "default",
  CLOSED: "outline",
  CANCELLED: "destructive",
};

export function TradePlansList() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [executeDialog, setExecuteDialog] = useState<{
    plan: Plan;
    type: "ENTRY" | "EXIT";
  } | null>(null);
  const [journalPrompt, setJournalPrompt] = useState<{
    symbol: string;
    journalId: string | null;
    pl: number | null;
    plPct: number | null;
  } | null>(null);
  const [writingJournal, setWritingJournal] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    fetch("/api/portfolio/plans")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.plans) {
          setPlans(res.data.plans);
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
    if (!confirm("Delete this trade plan? This cannot be undone.")) return;
    setDeletingId(id);
    try {
      const res = await fetch(`/api/portfolio/plans/${id}`, { method: "DELETE" });
      const json = await res.json();
      if (json.success) {
        setPlans((prev) => prev.filter((p) => p.id !== id));
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
  if (editingPlan) {
    return (
      <TradePlanForm
        plan={editingPlan}
        onSaved={() => {
          setEditingPlan(null);
          load();
        }}
        onCancel={() => setEditingPlan(null)}
      />
    );
  }

  if (plans.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Trade plans</CardTitle>
        </CardHeader>
        <CardContent className="text-muted-foreground py-8 text-center">
          No trade plans yet. Create one above.
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      {executeDialog && (
        <TradeExecuteDialog
          plan={executeDialog.plan}
          executeType={executeDialog.type}
          open={true}
          onClose={() => setExecuteDialog(null)}
          onSuccess={(result: ExecuteResult) => {
            const wasExit = executeDialog.type === "EXIT";
            setExecuteDialog(null);
            load();
            if (wasExit) {
              setJournalPrompt({
                symbol: executeDialog.plan.symbol,
                journalId: result.journalId,
                pl: result.pl,
                plPct: result.plPct,
              });
            }
          }}
        />
      )}

      {/* Journal prompt banner — shown after trade exits */}
      {journalPrompt && !writingJournal && (
        <div className={`rounded-xl border-2 p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
          (journalPrompt.pl ?? 0) >= 0
            ? "border-green-300 dark:border-green-700 bg-green-50 dark:bg-green-950/40"
            : "border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-950/40"
        }`}>
          <div className="space-y-1">
            <p className="font-semibold text-base">
              {(journalPrompt.pl ?? 0) >= 0 ? "🏆" : "📉"} Trade closed — {journalPrompt.symbol}
            </p>
            {journalPrompt.pl != null && (
              <p className={`text-2xl font-bold tabular-nums ${
                journalPrompt.pl >= 0 ? "text-green-700 dark:text-green-400" : "text-red-600 dark:text-red-400"
              }`}>
                {journalPrompt.pl >= 0 ? "+" : ""}Rs {journalPrompt.pl.toLocaleString("en-PK", { maximumFractionDigits: 0 })}
                {journalPrompt.plPct != null && (
                  <span className="text-sm font-normal text-muted-foreground ml-2">
                    ({journalPrompt.plPct >= 0 ? "+" : ""}{journalPrompt.plPct.toFixed(2)}%)
                  </span>
                )}
              </p>
            )}
            <p className="text-sm text-muted-foreground">
              Journal this trade while it&apos;s fresh — capture what worked, what didn&apos;t, and your lessons.
            </p>
          </div>
          <div className="flex gap-3 shrink-0">
            <Button
              onClick={() => setWritingJournal(true)}
              className="gap-1.5"
            >
              ✍️ Write journal entry
            </Button>
            <Button
              variant="outline"
              onClick={() => setJournalPrompt(null)}
            >
              Skip for now
            </Button>
          </div>
        </div>
      )}

      {/* Inline journal form — opened from prompt */}
      {journalPrompt && writingJournal && (
        <TradeJournalForm
          journalId={journalPrompt.journalId ?? undefined}
          tradePlanSymbol={journalPrompt.symbol}
          fromExit={true}
          onSaved={() => {
            setWritingJournal(false);
            setJournalPrompt(null);
          }}
          onCancel={() => setWritingJournal(false)}
        />
      )}

      <Card>
        <CardHeader>
          <CardTitle>Trade plans</CardTitle>
          <p className="text-sm text-muted-foreground">
            {plans.length} plan{plans.length !== 1 ? "s" : ""} · entry, target, stop loss and risk
          </p>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Symbol</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Dir</TableHead>
                <TableHead className="text-right">Entry</TableHead>
                <TableHead className="text-right">Target</TableHead>
                <TableHead className="text-right">Stop</TableHead>
                <TableHead className="text-right">R:R</TableHead>
                <TableHead className="text-right">Risk Rs</TableHead>
                <TableHead className="w-[140px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {plans.map((p) => (
                <TableRow key={p.id}>
                  <TableCell>
                    <div className="font-medium">{p.symbol}</div>
                    <div className="text-xs text-muted-foreground truncate max-w-[120px]">{p.name}</div>
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariant[p.status] ?? "outline"}>{p.status}</Badge>
                  </TableCell>
                  <TableCell>
                    <span className={p.direction === "LONG" ? "text-green-600 dark:text-green-400 font-medium" : "text-red-500 font-medium"}>
                      {p.direction}
                    </span>
                  </TableCell>
                  <TableCell className="text-right">{p.entryPrice.toFixed(2)}</TableCell>
                  <TableCell className="text-right">
                    {p.targetPrice != null ? p.targetPrice.toFixed(2) : "—"}
                  </TableCell>
                  <TableCell className="text-right">{p.stopLoss.toFixed(2)}</TableCell>
                  <TableCell className="text-right">
                    {p.rewardRiskRatio != null ? (
                      <span className={p.rewardRiskRatio >= 2 ? "text-green-600 dark:text-green-400" : "text-amber-600 dark:text-amber-400"}>
                        {p.rewardRiskRatio.toFixed(2)}
                      </span>
                    ) : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    {p.riskAmount != null
                      ? `${p.riskAmount.toLocaleString("en-PK", { maximumFractionDigits: 0 })}`
                      : "—"}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1 justify-end flex-wrap">
                      {(p.status === "PLANNED" || p.status === "ACTIVE") && (
                        <Button
                          size="sm"
                          variant={p.status === "PLANNED" ? "default" : "secondary"}
                          className="h-7 px-2 text-xs"
                          onClick={() => setExecuteDialog({ plan: p, type: "ENTRY" })}
                        >
                          Enter
                        </Button>
                      )}
                      {p.status === "ACTIVE" && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 px-2 text-xs text-amber-600 border-amber-300 hover:bg-amber-50 dark:text-amber-400 dark:border-amber-700 dark:hover:bg-amber-950"
                          onClick={() => setExecuteDialog({ plan: p, type: "EXIT" })}
                        >
                          Exit
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs"
                        onClick={() => setEditingPlan(p)}
                      >
                        Edit
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                        disabled={deletingId === p.id}
                        onClick={() => handleDelete(p.id)}
                      >
                        {deletingId === p.id ? "…" : "Del"}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </>
  );
}

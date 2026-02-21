"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type Entry = {
  id: string;
  tradePlanId: string;
  symbol: string;
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

type Draft = {
  entryDate: string;
  exitDate: string;
  entryPrice: string;
  exitPrice: string;
  quantity: string;
  strategyLabel: string;
  ideaSource: string;
  exitMethod: string;
  entryNotes: string;
  exitNotes: string;
  emotionalState: string;
  lessonsLearned: string;
};

function fmt(n: number, dec = 2) {
  return n.toLocaleString("en-PK", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function QualitativeSections({
  draft,
  set,
  fromExit,
}: {
  draft: Draft;
  set: (k: keyof Draft, v: string) => void;
  fromExit: boolean;
}) {
  const ta = "w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none";

  return (
    <>
      {/* Strategy + Source */}
      <section className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Strategy
        </p>
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>Strategy used</Label>
            <Input
              type="text"
              placeholder="e.g. Breakout, Mean Reversion, Support bounce"
              value={draft.strategyLabel}
              onChange={(e) => set("strategyLabel", e.target.value)}
              autoFocus={fromExit}
            />
          </div>
          <div className="space-y-2">
            <Label>Idea source <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Input
              type="text"
              placeholder="e.g. Chart scan, News, Peer discussion"
              value={draft.ideaSource}
              onChange={(e) => set("ideaSource", e.target.value)}
            />
          </div>
        </div>
      </section>

      {/* Exit analysis */}
      <section className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Exit analysis
        </p>
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
          <div className="space-y-2">
            <Label>How did it exit?</Label>
            <Input
              type="text"
              placeholder="e.g. Target hit, Stop hit, Manual, Held too long"
              value={draft.exitMethod}
              onChange={(e) => set("exitMethod", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Emotional state during trade</Label>
            <Input
              type="text"
              placeholder="e.g. Confident, Patient, FOMO, Anxious, Frustrated"
              value={draft.emotionalState}
              onChange={(e) => set("emotionalState", e.target.value)}
            />
          </div>
        </div>
      </section>

      {/* What went well / What went wrong */}
      <section className="space-y-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {fromExit ? "Wins, losses & analysis" : "Notes"}
        </p>
        <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
          <div className="space-y-2">
            <Label className="flex items-center gap-1.5">
              {fromExit && <span className="text-green-600 dark:text-green-400">✓</span>}
              {fromExit ? "What went well?" : "Entry notes"}
            </Label>
            <textarea
              rows={3}
              placeholder={fromExit
                ? "Setup was clean, risk was controlled, followed the plan…"
                : "Why you entered, market context, confirmation signals…"}
              value={draft.entryNotes}
              onChange={(e) => set("entryNotes", e.target.value)}
              className={ta}
            />
          </div>
          <div className="space-y-2">
            <Label className="flex items-center gap-1.5">
              {fromExit && <span className="text-red-500">✗</span>}
              {fromExit ? "What went wrong?" : "Exit notes"}
            </Label>
            <textarea
              rows={3}
              placeholder={fromExit
                ? "Exited too early, ignored the trend, let emotions drive…"
                : "Why you exited, what happened, any surprises…"}
              value={draft.exitNotes}
              onChange={(e) => set("exitNotes", e.target.value)}
              className={ta}
            />
          </div>
        </div>
      </section>

      {/* Lessons learned */}
      <section className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {fromExit ? "Lessons & what to do differently" : "Lessons & reflection"}
        </p>
        <textarea
          rows={4}
          placeholder={fromExit
            ? "What would you do differently? Rules to follow next time. What to repeat, what to avoid…"
            : "What did you learn? What would you do differently? Mistakes to avoid, wins to repeat…"}
          value={draft.lessonsLearned}
          onChange={(e) => set("lessonsLearned", e.target.value)}
          className={ta}
        />
      </section>
    </>
  );
}

function entryToDraft(entry: Entry): Draft {
  return {
    entryDate: entry.entryDate.split("T")[0],
    exitDate: entry.exitDate ? entry.exitDate.split("T")[0] : "",
    entryPrice: String(entry.entryPrice),
    exitPrice: entry.exitPrice != null ? String(entry.exitPrice) : "",
    quantity: String(entry.quantity),
    strategyLabel: entry.strategyLabel ?? "",
    ideaSource: entry.ideaSource ?? "",
    exitMethod: entry.exitMethod ?? "",
    entryNotes: entry.entryNotes ?? "",
    exitNotes: entry.exitNotes ?? "",
    emotionalState: entry.emotionalState ?? "",
    lessonsLearned: entry.lessonsLearned ?? "",
  };
}

const emptyDraft: Draft = {
  entryDate: new Date().toISOString().split("T")[0],
  exitDate: "",
  entryPrice: "",
  exitPrice: "",
  quantity: "",
  strategyLabel: "",
  ideaSource: "",
  exitMethod: "",
  entryNotes: "",
  exitNotes: "",
  emotionalState: "",
  lessonsLearned: "",
};

export function TradeJournalForm({
  entry: initialEntry,
  journalId,
  tradePlanSymbol,
  fromExit,
  onSaved,
  onCancel,
}: {
  entry?: Entry;
  journalId?: string;       // load by ID (post-exit flow)
  tradePlanSymbol: string;
  fromExit?: boolean;       // true = came from exit, qualitative fields highlighted
  onSaved: () => void;
  onCancel?: () => void;
}) {
  const isEdit = !!(initialEntry || journalId);
  const [loadedEntry, setLoadedEntry] = useState<Entry | null>(initialEntry ?? null);
  const [draft, setDraft] = useState<Draft>(() =>
    initialEntry ? entryToDraft(initialEntry) : { ...emptyDraft }
  );
  const [loadingEntry, setLoadingEntry] = useState(!!journalId && !initialEntry);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading] = useState(false);

  // Auto-load when journalId is provided (post-exit flow)
  useEffect(() => {
    if (!journalId || initialEntry) return;
    setLoadingEntry(true);
    fetch(`/api/portfolio/journal?id=${journalId}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.entry) {
          setLoadedEntry(res.data.entry);
          setDraft(entryToDraft(res.data.entry));
        }
      })
      .finally(() => setLoadingEntry(false));
  }, [journalId, initialEntry]);

  const activeEntry = loadedEntry ?? initialEntry;
  const activeId = activeEntry?.id ?? null;

  const set = (key: keyof Draft, val: string) =>
    setDraft((d) => ({ ...d, [key]: val }));

  // Live P&L calculation
  const entryP = parseFloat(draft.entryPrice);
  const exitP = parseFloat(draft.exitPrice);
  const qty = parseFloat(draft.quantity);

  let calcPL: number | null = null;
  let calcPLPct: number | null = null;
  if (isFinite(entryP) && isFinite(exitP) && isFinite(qty) && qty > 0) {
    calcPL = (exitP - entryP) * qty;
    calcPLPct = ((exitP - entryP) / entryP) * 100;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!draft.entryDate || !draft.entryPrice || !draft.quantity) {
      return setError("Entry date, price, and quantity are required.");
    }

    const entryP = parseFloat(draft.entryPrice);
    const qty = parseFloat(draft.quantity);
    if (!isFinite(entryP) || entryP <= 0 || !isFinite(qty) || qty <= 0) {
      return setError("Enter valid price and quantity.");
    }

    setSaving(true);
    try {
      const body = {
        ...(isEdit && activeId && { id: activeId }),
        entryDate: draft.entryDate,
        exitDate: draft.exitDate || null,
        entryPrice: entryP,
        exitPrice: draft.exitPrice ? parseFloat(draft.exitPrice) : null,
        quantity: qty,
        strategyLabel: draft.strategyLabel || null,
        ideaSource: draft.ideaSource || null,
        exitMethod: draft.exitMethod || null,
        entryNotes: draft.entryNotes || null,
        exitNotes: draft.exitNotes || null,
        emotionalState: draft.emotionalState || null,
        lessonsLearned: draft.lessonsLearned || null,
      };

      const url = isEdit && activeId
        ? `/api/portfolio/journal?id=${activeId}`
        : `/api/portfolio/journal`;
      const method = isEdit && activeId ? "PATCH" : "POST";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json = await res.json();

      if (json.success) {
        onSaved();
      } else {
        setError(json.error ?? "Save failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loadingEntry) {
    return (
      <Card>
        <CardHeader><CardTitle>Loading journal entry…</CardTitle></CardHeader>
        <CardContent><Skeleton className="h-48 w-full" /></CardContent>
      </Card>
    );
  }

  // P&L badge from loaded entry for the post-exit banner
  const loadedPL = activeEntry?.realizedPL;
  const loadedPLPct = activeEntry?.realizedPLPercent;

  return (
    <Card className={fromExit ? "border-2 border-primary/30" : ""}>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2">
              {fromExit ? "Write journal entry" : isEdit ? `Edit journal — ${tradePlanSymbol}` : "New journal entry"}
              {fromExit && <Badge variant="outline">{tradePlanSymbol}</Badge>}
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {fromExit
                ? "Trade closed — capture what worked, what didn't, and your lessons while it's fresh."
                : isEdit
                ? "Update the trade journal entry."
                : "Log details about your completed trade."}
            </p>
          </div>
          {/* P&L badge from executed exit */}
          {fromExit && loadedPL != null && (
            <div className={`shrink-0 rounded-lg border px-4 py-2 text-right ${
              loadedPL >= 0
                ? "border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-950/40"
                : "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40"
            }`}>
              <p className={`text-lg font-bold tabular-nums ${
                loadedPL >= 0 ? "text-green-700 dark:text-green-400" : "text-red-600 dark:text-red-400"
              }`}>
                {loadedPL >= 0 ? "+" : ""}Rs {loadedPL.toLocaleString("en-PK", { maximumFractionDigits: 0 })}
              </p>
              {loadedPLPct != null && (
                <p className="text-xs text-muted-foreground tabular-nums">
                  {loadedPLPct >= 0 ? "+" : ""}{loadedPLPct.toFixed(2)}%
                </p>
              )}
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-8">

          {/* Entry dates */}
          <section className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Trade dates
            </p>
            <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Entry date</Label>
                <Input
                  type="date"
                  value={draft.entryDate}
                  onChange={(e) => set("entryDate", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Exit date <span className="text-muted-foreground font-normal">(optional)</span></Label>
                <Input
                  type="date"
                  value={draft.exitDate}
                  onChange={(e) => set("exitDate", e.target.value)}
                />
              </div>
            </div>
          </section>

          {/* Prices and quantity */}
          <section className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Trade execution
            </p>
            <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
              <div className="space-y-2">
                <Label>Entry price (Rs)</Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="250.00"
                  value={draft.entryPrice}
                  onChange={(e) => set("entryPrice", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Exit price <span className="text-muted-foreground font-normal">(Rs, optional)</span></Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="280.00"
                  value={draft.exitPrice}
                  onChange={(e) => set("exitPrice", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Quantity (shares)</Label>
                <Input
                  type="number"
                  step="1"
                  min="1"
                  placeholder="500"
                  value={draft.quantity}
                  onChange={(e) => set("quantity", e.target.value)}
                />
              </div>
            </div>

          {/* Execution numbers are read-only when coming from exit */}
          {fromExit && activeEntry && (
            <p className="text-xs text-muted-foreground">
              Execution numbers were recorded automatically. Edit if needed.
            </p>
          )}

          {/* Live P&L preview */}
          {calcPL != null && calcPLPct != null && (
              <div className={`rounded-lg border px-4 py-3 ${
                calcPL >= 0
                  ? "border-green-200 dark:border-green-900 bg-green-50 dark:bg-green-950/30"
                  : "border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30"
              }`}>
                <p className={`text-sm font-semibold ${
                  calcPL >= 0
                    ? "text-green-700 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }`}>
                  Realized P&L: {calcPL >= 0 ? "+" : ""}Rs {fmt(calcPL)} ({calcPLPct >= 0 ? "+" : ""}{calcPLPct.toFixed(2)}%)
                </p>
              </div>
            )}
          </section>

          {/* When from exit: qualitative sections come FIRST, numbers after */}
          {fromExit && <QualitativeSections draft={draft} set={set} fromExit={fromExit} />}

          {/* Trade strategy and source — shown here only when NOT fromExit */}
          {!fromExit && <QualitativeSections draft={draft} set={set} fromExit={false} />}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex gap-3 pt-2">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : isEdit ? "Save entry" : "Create entry"}
            </Button>
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

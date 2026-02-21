"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type Stock = { id: string; ticker: string; name: string; sector: string };

type PlanDraft = {
  stockId: string;
  direction: "LONG" | "SHORT";
  status: "PLANNED" | "ACTIVE" | "CLOSED" | "CANCELLED";
  entryPrice: string;
  targetPrice: string;
  stopLoss: string;
  positionSize: string;
  notes: string;
};

type ExistingPlan = {
  id: string;
  stockId: string;
  symbol: string;
  direction: string;
  status: string;
  entryPrice: number;
  targetPrice: number | null;
  stopLoss: number;
  positionSize: number | null;
  riskAmount: number | null;
  rewardRiskRatio: number | null;
  notes: string | null;
};

const CHECKLIST_ITEMS = [
  "Trend confirmed on daily chart",
  "Volume supports the move",
  "Key support/resistance identified",
  "Stop loss placed below structure",
  "R:R ratio ≥ 2",
  "Sector is not overweight",
  "No earnings / announcement risk",
  "Position size within risk limits",
];

const empty: PlanDraft = {
  stockId: "",
  direction: "LONG",
  status: "PLANNED",
  entryPrice: "",
  targetPrice: "",
  stopLoss: "",
  positionSize: "",
  notes: "",
};

function calcDerived(draft: PlanDraft) {
  const entry = parseFloat(draft.entryPrice);
  const target = parseFloat(draft.targetPrice);
  const stop = parseFloat(draft.stopLoss);
  const size = parseFloat(draft.positionSize);

  if (!isFinite(entry) || !isFinite(stop) || entry <= 0 || stop <= 0) {
    return { rr: null, riskPct: null, riskAmt: null };
  }

  const isLong = draft.direction === "LONG";
  const riskPct = isLong
    ? ((entry - stop) / entry) * 100
    : ((stop - entry) / entry) * 100;

  let rr: number | null = null;
  if (isFinite(target) && target > 0) {
    const reward = isLong ? target - entry : entry - target;
    const risk = isLong ? entry - stop : stop - entry;
    rr = risk > 0 ? reward / risk : null;
  }

  const riskAmt =
    isFinite(size) && size > 0
      ? isLong
        ? size * (entry - stop)
        : size * (stop - entry)
      : null;

  return { rr, riskPct, riskAmt };
}

export function TradePlanForm({
  plan,
  onSaved,
  onCancel,
}: {
  plan?: ExistingPlan;
  onSaved: () => void;
  onCancel?: () => void;
}) {
  const isEdit = !!plan;
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [draft, setDraft] = useState<PlanDraft>(() =>
    plan
      ? {
          stockId: plan.stockId,
          direction: (plan.direction as PlanDraft["direction"]) ?? "LONG",
          status: (plan.status as PlanDraft["status"]) ?? "PLANNED",
          entryPrice: String(plan.entryPrice),
          targetPrice: plan.targetPrice != null ? String(plan.targetPrice) : "",
          stopLoss: String(plan.stopLoss),
          positionSize: plan.positionSize != null ? String(plan.positionSize) : "",
          notes: plan.notes ?? "",
        }
      : { ...empty }
  );
  const [checklist, setChecklist] = useState<Record<string, boolean>>(() => {
    if (plan?.notes) {
      try {
        const parsed = JSON.parse(plan.notes);
        if (typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
      } catch {}
    }
    return Object.fromEntries(CHECKLIST_ITEMS.map((item) => [item, false]));
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStocks = useCallback(() => {
    fetch("/api/stocks")
      .then((r) => r.json())
      .then((res) => {
        if (res.success) setStocks(res.data.stocks ?? []);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadStocks();
  }, [loadStocks]);

  const set = (field: keyof PlanDraft, value: string) =>
    setDraft((d) => ({ ...d, [field]: value }));

  const { rr, riskPct, riskAmt } = calcDerived(draft);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!draft.stockId) return setError("Select a stock.");
    if (!draft.entryPrice || !draft.stopLoss)
      return setError("Entry price and stop loss are required.");

    const checklistJson = JSON.stringify(checklist);
    const body = {
      stockId: draft.stockId,
      direction: draft.direction,
      status: draft.status,
      entryPrice: parseFloat(draft.entryPrice),
      targetPrice: draft.targetPrice ? parseFloat(draft.targetPrice) : null,
      stopLoss: parseFloat(draft.stopLoss),
      positionSize: draft.positionSize ? parseFloat(draft.positionSize) : null,
      riskAmount: riskAmt,
      rewardRiskRatio: rr,
      notes: draft.notes || null,
      checklist: checklistJson,
    };

    setSaving(true);
    try {
      const url = isEdit
        ? `/api/portfolio/plans/${plan!.id}`
        : "/api/portfolio/plans";
      const method = isEdit ? "PATCH" : "POST";
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      if (json.success) {
        onSaved();
        if (!isEdit) setDraft({ ...empty });
      } else {
        setError(json.error ?? "Save failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const selectedStock = stocks.find((s) => s.id === draft.stockId);

  const checkedCount = Object.values(checklist).filter(Boolean).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{isEdit ? `Edit plan — ${plan!.symbol}` : "New trade plan"}</CardTitle>
        <p className="text-sm text-muted-foreground">
          {isEdit ? "Update the trade plan details below." : "Fill in the details to create a new trade plan."}
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-8">

          {/* ── Section 1: Stock identity ── */}
          <section className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Stock
            </p>

            {/* Stock takes its own full row so the name never bleeds into other columns */}
            <div className="space-y-2">
              <Label>Stock</Label>
              {isEdit ? (
                <div className="flex h-9 w-full max-w-sm items-center rounded-md border border-input bg-muted px-3 text-sm font-medium">
                  <span className="font-semibold mr-2">{plan!.symbol}</span>
                  <span className="text-muted-foreground truncate">{plan!.symbol}</span>
                </div>
              ) : (
                <div className="max-w-sm">
                  <Select value={draft.stockId} onValueChange={(v) => set("stockId", v)}>
                    <SelectTrigger className="w-full">
                      {/* Show only ticker in trigger; full name appears in dropdown */}
                      <SelectValue placeholder="Select stock…">
                        {draft.stockId && selectedStock
                          ? (
                            <span className="flex items-center gap-2 min-w-0">
                              <span className="font-semibold shrink-0">{selectedStock.ticker}</span>
                              <span className="text-muted-foreground truncate text-xs">{selectedStock.name}</span>
                            </span>
                          )
                          : undefined}
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {stocks.map((s) => (
                        <SelectItem key={s.id} value={s.id}>
                          <span className="font-medium">{s.ticker}</span>
                          <span className="text-muted-foreground ml-2 text-sm">— {s.name}</span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {selectedStock && (
                    <p className="mt-1.5 text-xs text-muted-foreground">
                      Sector: <span className="font-medium text-foreground">{selectedStock.sector}</span>
                    </p>
                  )}
                </div>
              )}
            </div>

            {/* Direction + Status on their own smaller row */}
            <div className="grid gap-4 grid-cols-2 max-w-sm">
              <div className="space-y-2">
                <Label>Direction</Label>
                <Select
                  value={draft.direction}
                  onValueChange={(v) => set("direction", v as PlanDraft["direction"])}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="LONG">
                      <span className="text-green-600 dark:text-green-400 font-medium">LONG</span>
                    </SelectItem>
                    <SelectItem value="SHORT">
                      <span className="text-red-500 font-medium">SHORT</span>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  value={draft.status}
                  onValueChange={(v) => set("status", v as PlanDraft["status"])}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PLANNED">PLANNED</SelectItem>
                    <SelectItem value="ACTIVE">ACTIVE</SelectItem>
                    <SelectItem value="CLOSED">CLOSED</SelectItem>
                    <SelectItem value="CANCELLED">CANCELLED</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </section>

          {/* ── Section 2: Price levels + live metrics ── */}
          <section className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Price levels
            </p>

            <div className="grid gap-4 grid-cols-1 sm:grid-cols-3">
              <div className="space-y-2">
                <Label>Entry price <span className="text-muted-foreground font-normal">(Rs)</span></Label>
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
                <Label>
                  Target price{" "}
                  <span className="text-muted-foreground font-normal">(Rs, optional)</span>
                </Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="290.00"
                  value={draft.targetPrice}
                  onChange={(e) => set("targetPrice", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Stop loss <span className="text-muted-foreground font-normal">(Rs)</span></Label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="238.00"
                  value={draft.stopLoss}
                  onChange={(e) => set("stopLoss", e.target.value)}
                />
              </div>
            </div>
          </section>

          {/* ── Section 3: Position sizing + calculated metrics ── */}
          <section className="space-y-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Position sizing
            </p>

            <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>Position size <span className="text-muted-foreground font-normal">(shares)</span></Label>
                <Input
                  type="number"
                  step="1"
                  min="0"
                  placeholder="500"
                  value={draft.positionSize}
                  onChange={(e) => set("positionSize", e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Leave blank to calculate via Position Sizer on the Risk page.
                </p>
              </div>

              {/* Live metrics panel */}
              <div className="rounded-lg border border-border bg-muted/40 px-4 py-3 space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Calculated
                </p>

                <div className="flex items-center justify-between border-b border-border/50 pb-2">
                  <span className="text-sm text-muted-foreground">Risk %</span>
                  <span className={`text-sm font-semibold tabular-nums ${
                    riskPct != null && riskPct > 5
                      ? "text-destructive"
                      : riskPct != null
                      ? "text-foreground"
                      : "text-muted-foreground"
                  }`}>
                    {riskPct != null ? `${riskPct.toFixed(2)}%` : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-border/50 pb-2">
                  <span className="text-sm text-muted-foreground">Reward : Risk</span>
                  <span className={`text-sm font-semibold tabular-nums ${
                    rr == null
                      ? "text-muted-foreground"
                      : rr >= 2
                      ? "text-green-600 dark:text-green-400"
                      : "text-amber-600 dark:text-amber-400"
                  }`}>
                    {rr != null ? `${rr.toFixed(2)} : 1` : "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Risk amount</span>
                  <span className="text-sm font-semibold tabular-nums">
                    {riskAmt != null
                      ? `Rs ${riskAmt.toLocaleString("en-PK", { maximumFractionDigits: 0 })}`
                      : "—"}
                  </span>
                </div>
              </div>
            </div>
          </section>

          {/* ── Section 4: Notes ── */}
          <section className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Notes
            </p>
            <textarea
              rows={3}
              placeholder="Trade thesis, entry trigger, market context…"
              value={draft.notes}
              onChange={(e) => set("notes", e.target.value)}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
            />
          </section>

          {/* ── Section 5: Checklist ── */}
          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Trade checklist
              </p>
              <span className="text-xs text-muted-foreground">
                <span className={checkedCount === CHECKLIST_ITEMS.length ? "text-green-600 dark:text-green-400 font-semibold" : "font-medium text-foreground"}>
                  {checkedCount}
                </span>
                {" / "}{CHECKLIST_ITEMS.length}
              </span>
            </div>

            {/* Progress bar */}
            <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all duration-300"
                style={{ width: `${(checkedCount / CHECKLIST_ITEMS.length) * 100}%` }}
              />
            </div>

            <div className="rounded-lg border border-border divide-y divide-border/60">
              {CHECKLIST_ITEMS.map((item) => (
                <label
                  key={item}
                  className="flex items-center gap-3 px-3 py-2.5 cursor-pointer select-none hover:bg-muted/40 transition-colors first:rounded-t-lg last:rounded-b-lg"
                >
                  <input
                    type="checkbox"
                    checked={checklist[item] ?? false}
                    onChange={(e) =>
                      setChecklist((c) => ({ ...c, [item]: e.target.checked }))
                    }
                    className="rounded border-input accent-primary shrink-0"
                  />
                  <span className={`text-sm ${checklist[item] ? "line-through text-muted-foreground" : ""}`}>
                    {item}
                  </span>
                </label>
              ))}
            </div>
          </section>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <div className="flex gap-3 pt-1">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : isEdit ? "Save changes" : "Create plan"}
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

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

type Plan = {
  id: string;
  symbol: string;
  name: string;
  direction: string;
  entryPrice: number;
  stopLoss: number;
  targetPrice: number | null;
  positionSize: number | null;
  rewardRiskRatio: number | null;
};

type ExecuteType = "ENTRY" | "EXIT";

type RiskSettings = {
  accountValue: number;
  maxRiskPerTradePct: number;
  maxPositionSizePct: number;
  maxSinglePositionPct: number;
  minRewardRiskRatio: number;
};

type ValidationViolation = {
  id: string;
  message: string;
  detail: string;
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

function computeEntryViolations(
  price: number,
  quantity: number,
  plan: Plan,
  settings: RiskSettings | null
): ValidationViolation[] {
  if (!settings || settings.accountValue <= 0) return [];

  const positionValue = price * quantity;
  const isLong = plan.direction === "LONG";
  const riskPerShare = isLong ? price - plan.stopLoss : plan.stopLoss - price;
  const riskAmount = Math.abs(riskPerShare) * quantity;

  const riskPct = (riskAmount / settings.accountValue) * 100;
  const positionPct = (positionValue / settings.accountValue) * 100;

  let rr: number | null = null;
  if (plan.targetPrice != null && plan.targetPrice > 0 && riskPerShare > 0) {
    const reward = isLong ? plan.targetPrice - price : price - plan.targetPrice;
    rr = reward / riskPerShare;
  }

  const violations: ValidationViolation[] = [];

  if (riskPct > settings.maxRiskPerTradePct) {
    violations.push({
      id: "risk_pct",
      message: "Risk per trade exceeded",
      detail: `${riskPct.toFixed(2)}% > max ${settings.maxRiskPerTradePct}% (Rs ${riskAmount.toLocaleString("en-PK", { maximumFractionDigits: 0 })} at risk)`,
    });
  }
  if (positionPct > settings.maxPositionSizePct) {
    violations.push({
      id: "position_size",
      message: "Position size exceeded",
      detail: `${positionPct.toFixed(1)}% of account > max ${settings.maxPositionSizePct}% (Rs ${positionValue.toLocaleString("en-PK", { maximumFractionDigits: 0 })})`,
    });
  }
  if (positionPct > settings.maxSinglePositionPct) {
    violations.push({
      id: "single_position",
      message: "Single position limit exceeded",
      detail: `${positionPct.toFixed(1)}% > max ${settings.maxSinglePositionPct}% per position`,
    });
  }
  if (rr != null && rr < settings.minRewardRiskRatio) {
    violations.push({
      id: "rr",
      message: "Reward:Risk below minimum",
      detail: `${rr.toFixed(2)} : 1 < min ${settings.minRewardRiskRatio} : 1`,
    });
  }

  return violations;
}

export type ExecuteResult = {
  journalId: string | null;
  pl: number | null;
  plPct: number | null;
  exitPrice: number | null;
};

export function TradeExecuteDialog({
  plan,
  executeType,
  open,
  onClose,
  onSuccess,
}: {
  plan: Plan;
  executeType: ExecuteType;
  open: boolean;
  onClose: () => void;
  onSuccess: (result: ExecuteResult) => void;
}) {
  const isEntry = executeType === "ENTRY";

  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [price, setPrice] = useState(() =>
    isEntry ? String(plan.entryPrice) : ""
  );
  const [quantity, setQuantity] = useState(() =>
    plan.positionSize != null ? String(plan.positionSize) : ""
  );
  const [fees, setFees] = useState("0");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [riskSettings, setRiskSettings] = useState<RiskSettings | null>(null);
  const [validationStep, setValidationStep] = useState<{
    violations: ValidationViolation[];
  } | null>(null);
  const [accountValueInput, setAccountValueInput] = useState("");
  const [savingAccountValue, setSavingAccountValue] = useState(false);

  const accountValueMissing = isEntry && (!riskSettings || riskSettings.accountValue <= 0);

  const loadRiskSettings = () => {
    if (!open || !isEntry) return;
    fetch("/api/portfolio/risk-settings")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.settings) {
          const s = res.data.settings;
          const av = s.accountValue ?? 0;
          setRiskSettings({
            accountValue: av,
            maxRiskPerTradePct: s.maxRiskPerTradePct ?? 2,
            maxPositionSizePct: s.maxPositionSizePct ?? 10,
            maxSinglePositionPct: s.maxSinglePositionPct ?? 15,
            minRewardRiskRatio: s.minRewardRiskRatio ?? 2,
          });
        }
      })
      .catch(() => {});
  };

  useEffect(() => {
    if (open && isEntry) {
      loadRiskSettings();
    } else {
      setRiskSettings(null);
      setValidationStep(null);
      setAccountValueInput("");
    }
  }, [open, isEntry]);

  const handleSaveAccountValue = async () => {
    const val = parseFloat(accountValueInput);
    if (!isFinite(val) || val <= 0) return;
    setSavingAccountValue(true);
    try {
      const res = await fetch("/api/portfolio/risk-settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountValue: val }),
      });
      const json = await res.json();
      if (json.success && json.data?.settings) {
        const av = json.data.settings.accountValue ?? 0;
        setRiskSettings((prev) => prev ? { ...prev, accountValue: av } : {
          accountValue: av,
          maxRiskPerTradePct: 2,
          maxPositionSizePct: 10,
          maxSinglePositionPct: 15,
          minRewardRiskRatio: 2,
        });
      }
    } finally {
      setSavingAccountValue(false);
    }
  };

  // Live P&L preview for EXIT
  const entryPriceNum = plan.entryPrice;
  const exitPriceNum = parseFloat(price);
  const qtyNum = parseFloat(quantity);
  const feesNum = parseFloat(fees) || 0;

  const previewPL =
    !isEntry && isFinite(exitPriceNum) && isFinite(qtyNum) && qtyNum > 0
      ? (exitPriceNum - entryPriceNum) * qtyNum - feesNum
      : null;
  const previewPLPct =
    previewPL != null && entryPriceNum > 0
      ? ((exitPriceNum - entryPriceNum) / entryPriceNum) * 100
      : null;

  // Entry: show risk at the actual price vs stop
  const riskAtEntry =
    isEntry && isFinite(parseFloat(price)) && isFinite(qtyNum) && qtyNum > 0
      ? Math.abs(parseFloat(price) - plan.stopLoss) * qtyNum
      : null;

  const doExecute = async () => {
    const p = parseFloat(price);
    const q = parseFloat(quantity);
    setError(null);
    setSaving(true);
    try {
      const res = await fetch(`/api/portfolio/plans/${plan.id}/execute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type: executeType,
          date: new Date(date).toISOString(),
          price: p,
          quantity: q,
          fees: isFinite(feesNum) ? feesNum : 0,
          notes: notes.trim() || undefined,
        }),
      });
      const json = await res.json();
      if (json.success) {
        const exitPrice = executeType === "EXIT" ? p : null;
        const pl = executeType === "EXIT" && isFinite(qtyNum)
          ? (p - plan.entryPrice) * qtyNum - feesNum
          : null;
        const plPct = pl != null && plan.entryPrice > 0
          ? ((p - plan.entryPrice) / plan.entryPrice) * 100
          : null;
        onSuccess({
          journalId: json.data?.journalId ?? null,
          pl,
          plPct,
          exitPrice,
        });
        onClose();
      } else {
        setError(json.error ?? "Execute failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Execute failed");
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setValidationStep(null);

    const p = parseFloat(price);
    const q = parseFloat(quantity);
    if (!isFinite(p) || p <= 0) return setError("Enter a valid price.");
    if (!isFinite(q) || q <= 0) return setError("Enter a valid quantity.");
    if (!date) return setError("Select a date.");

    if (isEntry && riskSettings && riskSettings.accountValue > 0) {
      const violations = computeEntryViolations(p, q, plan, riskSettings);
      if (violations.length > 0) {
        setValidationStep({ violations });
        return;
      }
    }

    await doExecute();
  };

  const handleProceedAnyway = () => {
    setValidationStep(null);
    doExecute();
  };

  const showingValidation = validationStep != null;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) { setValidationStep(null); onClose(); } }}>
      <DialogContent className="max-w-md">
        {showingValidation ? (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                ⚠️ Pre-trade validation
              </DialogTitle>
              <DialogDescription>
                This entry would exceed one or more of your risk limits. You can go back to adjust size/price or proceed anyway.
              </DialogDescription>
            </DialogHeader>

            <div className="rounded-lg border-2 border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 p-4 space-y-3">
              <p className="text-sm font-semibold text-amber-800 dark:text-amber-200">
                Violations ({validationStep.violations.length})
              </p>
              <ul className="space-y-2">
                {validationStep.violations.map((v) => (
                  <li key={v.id} className="flex gap-2 text-sm">
                    <span className="text-amber-600 dark:text-amber-400 shrink-0">•</span>
                    <div>
                      <p className="font-medium text-foreground">{v.message}</p>
                      <p className="text-muted-foreground text-xs mt-0.5">{v.detail}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => setValidationStep(null)}
                className="flex-1"
              >
                Go back
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={handleProceedAnyway}
                disabled={saving}
                className="flex-1"
              >
                {saving ? "Saving…" : "Proceed anyway"}
              </Button>
            </div>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                {isEntry ? "Enter trade" : "Exit trade"}
                <Badge variant={isEntry ? "default" : "secondary"}>{plan.symbol}</Badge>
                <span className={`text-sm font-normal ${plan.direction === "LONG" ? "text-green-600 dark:text-green-400" : "text-red-500"}`}>
                  {plan.direction}
                </span>
              </DialogTitle>
              <DialogDescription>
                {isEntry
                  ? "Record the actual entry. This will create a BUY transaction and set the plan to ACTIVE."
                  : "Record the actual exit. This will create a SELL transaction, close the plan, and log a journal entry."}
              </DialogDescription>
            </DialogHeader>

            {/* Plan reference */}
            <div className="rounded-lg border border-border bg-muted/40 p-3 space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
                Plan reference
              </p>
              <Stat label="Planned entry" value={`Rs ${plan.entryPrice.toFixed(2)}`} />
              <Stat label="Stop loss" value={`Rs ${plan.stopLoss.toFixed(2)}`} />
              {plan.targetPrice != null && (
                <Stat label="Target" value={`Rs ${plan.targetPrice.toFixed(2)}`} />
              )}
              {plan.rewardRiskRatio != null && (
                <Stat
                  label="R:R"
                  value={`${plan.rewardRiskRatio.toFixed(2)} : 1`}
                />
              )}
            </div>

            {/* Portfolio size — show when entering and account value not set */}
            {accountValueMissing && (
              <div className="rounded-lg border-2 border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/40 p-4 space-y-3">
                <p className="text-sm font-semibold text-amber-900 dark:text-amber-100">
                  Set portfolio size first
                </p>
                <p className="text-xs text-amber-800 dark:text-amber-200">
                  Pre-trade validation needs your total portfolio (account) value to check position size and risk limits. Enter it below or in Risk Settings.
                </p>
                <div className="flex gap-2 items-end">
                  <div className="space-y-1 flex-1">
                    <Label className="text-xs">Account value (Rs)</Label>
                    <Input
                      type="number"
                      min="1"
                      step="1000"
                      placeholder="e.g. 1000000"
                      value={accountValueInput}
                      onChange={(e) => setAccountValueInput(e.target.value)}
                    />
                  </div>
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleSaveAccountValue}
                    disabled={savingAccountValue || !accountValueInput.trim() || parseFloat(accountValueInput) <= 0}
                  >
                    {savingAccountValue ? "Saving…" : "Save"}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Or set it with full risk rules in{" "}
                  <Link href="/dashboard/risk" className="underline text-foreground hover:no-underline" onClick={() => onClose()}>
                    Risk Settings
                  </Link>
                </p>
              </div>
            )}

            {isEntry && riskSettings && riskSettings.accountValue > 0 && (
              <p className="text-xs text-muted-foreground">
                Portfolio size: <span className="font-semibold text-foreground">Rs {riskSettings.accountValue.toLocaleString("en-PK", { maximumFractionDigits: 0 })}</span>
                {" · "}
                <Link href="/dashboard/risk" className="underline hover:no-underline">Change in Risk Settings</Link>
              </p>
            )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Date</Label>
              <Input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Actual price (Rs)</Label>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder={isEntry ? String(plan.entryPrice) : "Exit price"}
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Quantity (shares)</Label>
              <Input
                type="number"
                step="1"
                min="1"
                placeholder={plan.positionSize != null ? String(plan.positionSize) : ""}
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>Fees (Rs)</Label>
              <Input
                type="number"
                step="0.01"
                min="0"
                placeholder="0"
                value={fees}
                onChange={(e) => setFees(e.target.value)}
              />
            </div>
          </div>

          {/* Live preview */}
          {isEntry && riskAtEntry != null && (
            <div className="rounded-md border border-amber-200 dark:border-amber-900 bg-amber-50 dark:bg-amber-950/30 px-3 py-2 text-sm space-y-0.5">
              <p className="text-amber-700 dark:text-amber-400 font-medium text-xs uppercase tracking-wide">
                Risk at this entry
              </p>
              <p className="font-semibold">
                Rs {riskAtEntry.toLocaleString("en-PK", { maximumFractionDigits: 0 })}
              </p>
            </div>
          )}

          {!isEntry && previewPL != null && (
            <div className={`rounded-md border px-3 py-2 text-sm space-y-0.5 ${
              previewPL >= 0
                ? "border-green-200 dark:border-green-900 bg-green-50 dark:bg-green-950/30"
                : "border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950/30"
            }`}>
              <p className={`font-medium text-xs uppercase tracking-wide ${
                previewPL >= 0 ? "text-green-700 dark:text-green-400" : "text-red-600 dark:text-red-400"
              }`}>
                Realized P&amp;L preview
              </p>
              <p className="font-semibold">
                {previewPL >= 0 ? "+" : ""}Rs {previewPL.toLocaleString("en-PK", { maximumFractionDigits: 0 })}
                {previewPLPct != null && (
                  <span className="text-xs font-normal ml-1 text-muted-foreground">
                    ({previewPLPct >= 0 ? "+" : ""}{previewPLPct.toFixed(2)}%)
                  </span>
                )}
              </p>
            </div>
          )}

          <div className="space-y-2">
            <Label>Notes (optional)</Label>
            <Input
              type="text"
              placeholder={isEntry ? "Entry trigger, market conditions…" : "Exit reason, lessons…"}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex gap-3 pt-1">
            <Button type="submit" disabled={saving} className="flex-1">
              {saving
                ? "Saving…"
                : isEntry
                ? "Confirm entry"
                : "Confirm exit"}
            </Button>
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
          </div>
        </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

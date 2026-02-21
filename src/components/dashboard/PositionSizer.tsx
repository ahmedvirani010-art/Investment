"use client";

import { useEffect, useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type RiskSettings = {
  accountValue: number;
  maxRiskPerTradePct: number;
  maxPositionSizePct: number;
  maxSinglePositionPct: number;
  maxTotalRiskPct: number;
  defaultStopLossPct: number;
  minRewardRiskRatio: number;
  useKellyCriterion: boolean;
  kellyFraction: number;
};

type Result = {
  shares: number;
  positionValue: number;
  riskAmount: number;
  riskPct: number;
  positionPct: number;
  rr: number | null;
  kellyShares: number | null;
  kellyPositionValue: number | null;
  kellyPct: number | null;
  violations: { label: string; detail: string }[];
};

function fmt(n: number, dec = 0) {
  return n.toLocaleString("en-PK", { minimumFractionDigits: dec, maximumFractionDigits: dec });
}

function Row({ label, value, sub, highlight }: { label: string; value: string; sub?: string; highlight?: "green" | "red" | "amber" }) {
  const color =
    highlight === "green" ? "text-green-600 dark:text-green-400"
    : highlight === "red" ? "text-red-600 dark:text-red-400"
    : highlight === "amber" ? "text-amber-600 dark:text-amber-400"
    : "";
  return (
    <div className="flex items-baseline justify-between py-1.5 border-b border-border/50 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={`text-sm font-semibold ${color}`}>
        {value}
        {sub && <span className="text-xs font-normal text-muted-foreground ml-1">{sub}</span>}
      </span>
    </div>
  );
}

export function PositionSizer() {
  const [settings, setSettings] = useState<RiskSettings | null>(null);
  const [loading, setLoading] = useState(true);

  // Inputs
  const [entry, setEntry] = useState("");
  const [stop, setStop] = useState("");
  const [target, setTarget] = useState("");
  const [customRiskPct, setCustomRiskPct] = useState("");
  const [winRate, setWinRate] = useState("50");   // for Kelly

  useEffect(() => {
    fetch("/api/portfolio/risk-settings")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.settings) {
          setSettings(res.data.settings);
          setCustomRiskPct(String(res.data.settings.maxRiskPerTradePct));
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const result = useMemo<Result | null>(() => {
    if (!settings) return null;

    const entryN = parseFloat(entry);
    const stopN = parseFloat(stop);
    const targetN = parseFloat(target);
    const riskPct = parseFloat(customRiskPct) || settings.maxRiskPerTradePct;
    const winRateN = Math.min(Math.max(parseFloat(winRate) / 100 || 0.5, 0.01), 0.99);

    if (!isFinite(entryN) || !isFinite(stopN) || entryN <= 0 || stopN <= 0) return null;

    const riskPerShare = Math.abs(entryN - stopN);
    if (riskPerShare === 0) return null;

    const accountVal = settings.accountValue;
    const riskAmount = (accountVal * riskPct) / 100;
    const shares = Math.floor(riskAmount / riskPerShare);
    if (shares <= 0) return null;

    const positionValue = shares * entryN;
    const positionPct = accountVal > 0 ? (positionValue / accountVal) * 100 : 0;
    const actualRiskPct = accountVal > 0 ? (riskAmount / accountVal) * 100 : 0;

    // R:R
    let rr: number | null = null;
    if (isFinite(targetN) && targetN > 0) {
      const reward = Math.abs(targetN - entryN);
      rr = reward / riskPerShare;
    }

    // Kelly Criterion
    let kellyShares: number | null = null;
    let kellyPositionValue: number | null = null;
    let kellyPct: number | null = null;

    if (settings.useKellyCriterion && rr != null) {
      // Kelly% = W - (1-W)/R  where W=win rate, R=reward/risk
      const rawKelly = winRateN - (1 - winRateN) / rr;
      const fractionalKelly = Math.max(0, rawKelly * settings.kellyFraction);
      kellyPct = fractionalKelly * 100;
      kellyPositionValue = accountVal * fractionalKelly;
      kellyShares = Math.floor(kellyPositionValue / entryN);
    }

    // Violations
    const violations: { label: string; detail: string }[] = [];

    if (positionPct > settings.maxPositionSizePct) {
      violations.push({
        label: "Max position size exceeded",
        detail: `${positionPct.toFixed(1)}% > limit ${settings.maxPositionSizePct}%`,
      });
    }
    if (positionPct > settings.maxSinglePositionPct) {
      violations.push({
        label: "Max single position exceeded",
        detail: `${positionPct.toFixed(1)}% > limit ${settings.maxSinglePositionPct}%`,
      });
    }
    if (rr != null && rr < settings.minRewardRiskRatio) {
      violations.push({
        label: "R:R below minimum",
        detail: `${rr.toFixed(2)} < min ${settings.minRewardRiskRatio}`,
      });
    }
    if (accountVal === 0) {
      violations.push({
        label: "Account value not set",
        detail: "Set account value in Risk Settings",
      });
    }

    return {
      shares,
      positionValue,
      riskAmount,
      riskPct: actualRiskPct,
      positionPct,
      rr,
      kellyShares,
      kellyPositionValue,
      kellyPct,
      violations,
    };
  }, [settings, entry, stop, target, customRiskPct, winRate]);

  if (loading) {
    return (
      <Card>
        <CardHeader><CardTitle>Position Sizer</CardTitle></CardHeader>
        <CardContent><Skeleton className="h-48 w-full" /></CardContent>
      </Card>
    );
  }

  if (!settings) {
    return (
      <Card>
        <CardContent className="py-6 text-muted-foreground text-sm">
          No risk settings found. Add them in the Risk Settings panel below.
        </CardContent>
      </Card>
    );
  }

  const accountVal = settings.accountValue;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Position Sizer</CardTitle>
        <p className="text-sm text-muted-foreground">
          Calculate position size based on your risk settings
          {accountVal > 0 && (
            <span className="ml-1">· Account: <span className="font-medium text-foreground">Rs {fmt(accountVal)}</span></span>
          )}
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Inputs */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-2">
            <Label>Entry price (Rs)</Label>
            <Input
              type="number"
              step="0.01"
              min="0"
              placeholder="e.g. 250.00"
              value={entry}
              onChange={(e) => setEntry(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Stop loss (Rs)</Label>
            <Input
              type="number"
              step="0.01"
              min="0"
              placeholder="e.g. 238.00"
              value={stop}
              onChange={(e) => setStop(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Target price (Rs) <span className="text-muted-foreground font-normal">(optional)</span></Label>
            <Input
              type="number"
              step="0.01"
              min="0"
              placeholder="e.g. 280.00"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Risk % per trade</Label>
            <Input
              type="number"
              step="0.1"
              min="0.1"
              max="10"
              placeholder={String(settings.maxRiskPerTradePct)}
              value={customRiskPct}
              onChange={(e) => setCustomRiskPct(e.target.value)}
            />
          </div>
        </div>

        {/* Kelly win-rate input (only shown when Kelly is enabled) */}
        {settings.useKellyCriterion && (
          <div className="flex items-end gap-4">
            <div className="space-y-2 w-48">
              <Label>Win rate % <span className="text-muted-foreground font-normal">(for Kelly)</span></Label>
              <Input
                type="number"
                step="1"
                min="1"
                max="99"
                placeholder="50"
                value={winRate}
                onChange={(e) => setWinRate(e.target.value)}
              />
            </div>
            <p className="text-xs text-muted-foreground pb-2">
              Kelly fraction: {settings.kellyFraction} (fractional Kelly applied)
            </p>
          </div>
        )}

        {/* Results */}
        {result ? (
          <div className="grid gap-4 md:grid-cols-2">
            {/* Fixed % Risk method */}
            <div className="rounded-lg border border-border p-4 space-y-0">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                Fixed % Risk method
              </p>
              <Row
                label="Position size"
                value={`${fmt(result.shares)} shares`}
                highlight={result.violations.length === 0 ? "green" : "amber"}
              />
              <Row
                label="Position value"
                value={`Rs ${fmt(result.positionValue)}`}
                sub={`(${result.positionPct.toFixed(1)}% of account)`}
                highlight={result.positionPct > settings.maxSinglePositionPct ? "red" : undefined}
              />
              <Row
                label="Risk amount"
                value={`Rs ${fmt(result.riskAmount)}`}
                sub={`(${result.riskPct.toFixed(2)}%)`}
              />
              <Row
                label="Risk per share"
                value={`Rs ${Math.abs(parseFloat(entry) - parseFloat(stop)).toFixed(2)}`}
              />
              {result.rr != null && (
                <Row
                  label="Reward : Risk"
                  value={`${result.rr.toFixed(2)} : 1`}
                  highlight={result.rr >= settings.minRewardRiskRatio ? "green" : "red"}
                />
              )}
            </div>

            {/* Kelly / Violations */}
            <div className="space-y-4">
              {settings.useKellyCriterion && result.kellyShares != null && result.rr != null ? (
                <div className="rounded-lg border border-border p-4 space-y-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
                    Kelly criterion ({(settings.kellyFraction * 100).toFixed(0)}% fractional)
                  </p>
                  <Row
                    label="Kelly size"
                    value={`${fmt(result.kellyShares)} shares`}
                    highlight="green"
                  />
                  <Row
                    label="Kelly value"
                    value={`Rs ${fmt(result.kellyPositionValue ?? 0)}`}
                    sub={result.kellyPct != null ? `(${result.kellyPct.toFixed(1)}%)` : undefined}
                  />
                </div>
              ) : settings.useKellyCriterion ? (
                <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
                  Enter a target price to calculate Kelly position size.
                </div>
              ) : null}

              {result.violations.length > 0 && (
                <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-destructive mb-1">
                    Violations
                  </p>
                  {result.violations.map((v, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <Badge variant="destructive" className="text-xs shrink-0">!</Badge>
                      <div>
                        <p className="text-sm font-medium text-destructive">{v.label}</p>
                        <p className="text-xs text-muted-foreground">{v.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {result.violations.length === 0 && (
                <div className="rounded-lg border border-green-200 dark:border-green-900 bg-green-50 dark:bg-green-950/30 p-4">
                  <p className="text-sm font-medium text-green-700 dark:text-green-400">
                    ✓ Within all risk limits
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Position size, risk %, and R:R all pass your rules.
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
            Enter entry and stop loss prices to calculate position size.
          </div>
        )}

        {/* Quick reference */}
        <div className="rounded-lg bg-muted/40 border border-border p-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div>
            <p className="text-muted-foreground">Max risk / trade</p>
            <p className="font-semibold">{settings.maxRiskPerTradePct}%</p>
          </div>
          <div>
            <p className="text-muted-foreground">Max position size</p>
            <p className="font-semibold">{settings.maxPositionSizePct}%</p>
          </div>
          <div>
            <p className="text-muted-foreground">Min R:R</p>
            <p className="font-semibold">{settings.minRewardRiskRatio} : 1</p>
          </div>
          <div>
            <p className="text-muted-foreground">Default stop loss</p>
            <p className="font-semibold">{settings.defaultStopLossPct}%</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

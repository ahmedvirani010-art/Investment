"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

type Settings = {
  accountValue: number;
  maxRiskPerTradePct: number;
  maxPositionSizePct: number;
  maxTotalRiskPct: number;
  maxSectorExposurePct: number;
  maxSinglePositionPct: number;
  minPositions: number;
  maxPositions: number;
  defaultStopLossPct: number;
  minRewardRiskRatio: number;
  useKellyCriterion: boolean;
  kellyFraction: number;
  allowPyramiding: boolean;
  maxCorrelatedPositions: number;
};

const DEFAULTS: Settings = {
  accountValue: 0,
  maxRiskPerTradePct: 2,
  maxPositionSizePct: 10,
  maxTotalRiskPct: 6,
  maxSectorExposurePct: 30,
  maxSinglePositionPct: 15,
  minPositions: 5,
  maxPositions: 20,
  defaultStopLossPct: 3,
  minRewardRiskRatio: 2,
  useKellyCriterion: false,
  kellyFraction: 0.25,
  allowPyramiding: true,
  maxCorrelatedPositions: 3,
};

function NumField({
  label,
  hint,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  hint?: string;
  value: string;
  onChange: (v: string) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <div className="space-y-1.5">
      <Label className="text-sm">{label}</Label>
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      <Input
        type="number"
        min={min}
        max={max}
        step={step ?? 0.1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start gap-3">
      <input
        type="checkbox"
        id={label}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 rounded border-input accent-primary"
      />
      <div>
        <label htmlFor={label} className="text-sm font-medium cursor-pointer">{label}</label>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
    </div>
  );
}

export function RiskSettingsEditor({ onSaved }: { onSaved?: () => void }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  // Draft state — strings so inputs can be freely edited
  const [d, setD] = useState<Record<string, string>>({});
  const [bools, setBools] = useState({
    useKellyCriterion: false,
    allowPyramiding: true,
  });

  useEffect(() => {
    fetch("/api/portfolio/risk-settings")
      .then((r) => r.json())
      .then((res) => {
        const s: Settings = res.data?.settings ?? DEFAULTS;
        setD({
          accountValue: String(s.accountValue),
          maxRiskPerTradePct: String(s.maxRiskPerTradePct),
          maxPositionSizePct: String(s.maxPositionSizePct),
          maxTotalRiskPct: String(s.maxTotalRiskPct),
          maxSectorExposurePct: String(s.maxSectorExposurePct),
          maxSinglePositionPct: String(s.maxSinglePositionPct),
          minPositions: String(s.minPositions),
          maxPositions: String(s.maxPositions),
          defaultStopLossPct: String(s.defaultStopLossPct),
          minRewardRiskRatio: String(s.minRewardRiskRatio),
          kellyFraction: String(s.kellyFraction),
          maxCorrelatedPositions: String(s.maxCorrelatedPositions),
        });
        setBools({
          useKellyCriterion: s.useKellyCriterion,
          allowPyramiding: s.allowPyramiding,
        });
      })
      .finally(() => setLoading(false));
  }, []);

  const f = (key: string) => d[key] ?? "";
  const set = (key: string, v: string) => setD((prev) => ({ ...prev, [key]: v }));

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaved(false);
    setSaving(true);

    try {
      const body = {
        accountValue: parseFloat(f("accountValue")) || 0,
        maxRiskPerTradePct: parseFloat(f("maxRiskPerTradePct")),
        maxPositionSizePct: parseFloat(f("maxPositionSizePct")),
        maxTotalRiskPct: parseFloat(f("maxTotalRiskPct")),
        maxSectorExposurePct: parseFloat(f("maxSectorExposurePct")),
        maxSinglePositionPct: parseFloat(f("maxSinglePositionPct")),
        minPositions: parseInt(f("minPositions"), 10),
        maxPositions: parseInt(f("maxPositions"), 10),
        defaultStopLossPct: parseFloat(f("defaultStopLossPct")),
        minRewardRiskRatio: parseFloat(f("minRewardRiskRatio")),
        useKellyCriterion: bools.useKellyCriterion,
        kellyFraction: parseFloat(f("kellyFraction")),
        allowPyramiding: bools.allowPyramiding,
        maxCorrelatedPositions: parseInt(f("maxCorrelatedPositions"), 10),
      };

      const res = await fetch("/api/portfolio/risk-settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const json = await res.json();
      if (json.success) {
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
        onSaved?.();
      } else {
        setError(json.error ?? "Save failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader><CardTitle>Risk Settings</CardTitle></CardHeader>
        <CardContent><Skeleton className="h-64 w-full" /></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Risk Settings</CardTitle>
        <p className="text-sm text-muted-foreground">
          Configure account value and risk rules used by the Position Sizer and Risk Summary.
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSave} className="space-y-6">

          {/* Account */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Account</p>
            <div className="grid gap-4 md:grid-cols-2">
              <NumField
                label="Account value (Rs)"
                hint="Total capital available for trading"
                value={f("accountValue")}
                onChange={(v) => set("accountValue", v)}
                min={0}
                step={1000}
              />
            </div>
          </div>

          {/* Trade risk rules */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Trade risk rules</p>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <NumField
                label="Max risk per trade (%)"
                hint="% of account risked on a single trade"
                value={f("maxRiskPerTradePct")}
                onChange={(v) => set("maxRiskPerTradePct", v)}
                min={0.1} max={10} step={0.1}
              />
              <NumField
                label="Max position size (%)"
                hint="Max % of account in any one trade"
                value={f("maxPositionSizePct")}
                onChange={(v) => set("maxPositionSizePct", v)}
                min={1} max={100} step={1}
              />
              <NumField
                label="Max single position (%)"
                hint="Hard cap on one position's portfolio weight"
                value={f("maxSinglePositionPct")}
                onChange={(v) => set("maxSinglePositionPct", v)}
                min={1} max={100} step={1}
              />
              <NumField
                label="Max total risk (%)"
                hint="Max combined open risk across all trades"
                value={f("maxTotalRiskPct")}
                onChange={(v) => set("maxTotalRiskPct", v)}
                min={1} max={50} step={0.5}
              />
              <NumField
                label="Default stop loss (%)"
                hint="Default stop distance from entry"
                value={f("defaultStopLossPct")}
                onChange={(v) => set("defaultStopLossPct", v)}
                min={0.5} max={20} step={0.5}
              />
              <NumField
                label="Min reward : risk ratio"
                hint="Minimum acceptable R:R for a trade"
                value={f("minRewardRiskRatio")}
                onChange={(v) => set("minRewardRiskRatio", v)}
                min={0.5} max={10} step={0.5}
              />
            </div>
          </div>

          {/* Portfolio diversification */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Portfolio diversification</p>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <NumField
                label="Min positions"
                value={f("minPositions")}
                onChange={(v) => set("minPositions", v)}
                min={1} max={50} step={1}
              />
              <NumField
                label="Max positions"
                value={f("maxPositions")}
                onChange={(v) => set("maxPositions", v)}
                min={1} max={100} step={1}
              />
              <NumField
                label="Max sector exposure (%)"
                value={f("maxSectorExposurePct")}
                onChange={(v) => set("maxSectorExposurePct", v)}
                min={5} max={100} step={5}
              />
              <NumField
                label="Max correlated positions"
                hint="Max number of correlated / same-sector positions"
                value={f("maxCorrelatedPositions")}
                onChange={(v) => set("maxCorrelatedPositions", v)}
                min={1} max={20} step={1}
              />
            </div>
          </div>

          {/* Advanced */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">Advanced</p>
            <div className="space-y-3">
              <Toggle
                label="Use Kelly Criterion"
                hint="Show Kelly-based position size alongside fixed % risk in the Position Sizer"
                checked={bools.useKellyCriterion}
                onChange={(v) => setBools((b) => ({ ...b, useKellyCriterion: v }))}
              />
              {bools.useKellyCriterion && (
                <div className="ml-6 w-48">
                  <NumField
                    label="Kelly fraction"
                    hint="Fractional Kelly multiplier (0.25 = 25% Kelly)"
                    value={f("kellyFraction")}
                    onChange={(v) => set("kellyFraction", v)}
                    min={0.05} max={1} step={0.05}
                  />
                </div>
              )}
              <Toggle
                label="Allow pyramiding"
                hint="Allow adding to winning positions"
                checked={bools.allowPyramiding}
                onChange={(v) => setBools((b) => ({ ...b, allowPyramiding: v }))}
              />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex items-center gap-4">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save settings"}
            </Button>
            {saved && (
              <p className="text-sm text-green-600 dark:text-green-400">
                ✓ Settings saved
              </p>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

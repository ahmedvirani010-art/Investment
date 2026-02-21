"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export function AddCashForm({ onSuccess }: { onSuccess?: () => void }) {
  const [amount, setAmount] = useState("");
  const [currentAccountValue, setCurrentAccountValue] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch("/api/portfolio/risk-settings")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.settings?.accountValue != null) {
          setCurrentAccountValue(Number(res.data.settings.accountValue));
        } else {
          setCurrentAccountValue(0);
        }
      })
      .catch(() => setCurrentAccountValue(0))
      .finally(() => setLoading(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const num = parseFloat(amount);
    if (!isFinite(num) || num <= 0) {
      toast.error("Enter a valid amount (Rs).");
      return;
    }

    setSaving(true);
    try {
      const newValue = (currentAccountValue ?? 0) + num;
      const res = await fetch("/api/portfolio/risk-settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accountValue: newValue }),
      });
      const json = await res.json();
      if (json.success) {
        setCurrentAccountValue(newValue);
        setAmount("");
        toast.success(`Added Rs ${num.toLocaleString("en-PK", { maximumFractionDigits: 0 })}. Account value: Rs ${newValue.toLocaleString("en-PK", { maximumFractionDigits: 0 })}`);
        onSuccess?.();
      } else {
        toast.error(json.error ?? "Failed to update account value");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader><CardTitle className="text-base">Add cash</CardTitle></CardHeader>
        <CardContent><p className="text-sm text-muted-foreground">Loading…</p></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Add cash</CardTitle>
        <p className="text-sm text-muted-foreground">
          Record a deposit to update your portfolio (account) value for position sizing and risk checks.
          {currentAccountValue != null && currentAccountValue > 0 && (
            <span className="block mt-1 font-medium text-foreground">
              Current account value: Rs {currentAccountValue.toLocaleString("en-PK", { maximumFractionDigits: 0 })}
            </span>
          )}
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3">
          <div className="space-y-2 min-w-[140px]">
            <Label htmlFor="add-cash-amount">Amount (Rs)</Label>
            <Input
              id="add-cash-amount"
              type="number"
              min="1"
              step="1000"
              placeholder="e.g. 50000"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={saving}>
            {saving ? "Adding…" : "Add cash"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

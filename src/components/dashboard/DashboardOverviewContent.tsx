"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { PortfolioMetrics } from "@/components/dashboard/PortfolioMetrics";
import { PositionTable } from "@/components/dashboard/PositionTable";
import { PortfolioExportDropdown } from "@/components/dashboard/PortfolioExportDropdown";
import { AddTransactionForm } from "@/components/dashboard/AddTransactionForm";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Plus, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export function DashboardOverviewContent() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [addTxOpen, setAddTxOpen] = useState(false);
  const [syncingPrices, setSyncingPrices] = useState(false);
  const hasRunInitialSync = useRef(false);

  const runPriceSync = useCallback(() => {
    setSyncingPrices(true);
    fetch("/api/prices/sync", { method: "POST" })
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data: res }) => {
        if (ok && res.success && res.data) {
          const { updated = 0, errors = [], total = 0 } = res.data;
          setRefreshKey((k) => k + 1);
          if (errors.length > 0) {
            const failedList = errors.map((e: { ticker: string }) => e.ticker).join(", ");
            toast.warning(
              `Prices updated: ${updated}/${total}. ${errors.length} failed: ${failedList}`,
              { duration: 12000 }
            );
          } else {
            toast.success(`Prices updated for ${updated} stock${updated !== 1 ? "s" : ""}.`);
          }
        } else {
          toast.error(res?.details ?? res?.error ?? "Failed to sync prices");
        }
      })
      .catch((err) => {
        const msg = err?.name === "AbortError" ? "Request aborted" : "Failed to sync prices";
        toast.error(msg);
      })
      .finally(() => setSyncingPrices(false));
  }, []);

  // Sync prices when portfolio page loads (once per mount)
  useEffect(() => {
    if (hasRunInitialSync.current) return;
    hasRunInitialSync.current = true;
    runPriceSync();
  }, [runPriceSync]);

  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            Portfolio Overview
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Current holdings and portfolio summary
            {syncingPrices && (
              <span className="ml-2 text-muted-foreground/80">· Updating prices…</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={runPriceSync}
            disabled={syncingPrices}
            className="gap-1.5"
          >
            <RefreshCw className={`size-4 ${syncingPrices ? "animate-spin" : ""}`} />
            {syncingPrices ? "Updating…" : "Refresh prices"}
          </Button>
          <Button onClick={() => setAddTxOpen(true)} className="gap-1.5">
            <Plus className="size-4" />
            Add transaction
          </Button>
        </div>
      </div>

      <Dialog open={addTxOpen} onOpenChange={setAddTxOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Add transaction</DialogTitle>
            <DialogDescription>
              Record a buy, sell, cash or bonus dividend, or add cash (deposit). Cash updates account value for position sizing. Optionally link to a trade plan.
            </DialogDescription>
          </DialogHeader>
          <AddTransactionForm
            embedded
            onSuccess={() => {
              setRefreshKey((k) => k + 1);
              setAddTxOpen(false);
            }}
          />
        </DialogContent>
      </Dialog>

      <PortfolioMetrics key={`metrics-${refreshKey}`} />
      <div className="space-y-3">
        <div className="flex justify-end">
          <PortfolioExportDropdown />
        </div>
        <PositionTable key={`positions-${refreshKey}`} />
      </div>
    </div>
  );
}

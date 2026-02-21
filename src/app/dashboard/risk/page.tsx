"use client";

import Link from "next/link";
import { RiskSummary } from "@/components/dashboard/RiskSummary";
import { PositionSizer } from "@/components/dashboard/PositionSizer";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";

export default function RiskPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Risk Management</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Position sizing and portfolio risk metrics. Configure account value and risk rules in Settings.
          </p>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href="/dashboard/settings" className="gap-1.5">
            <Settings className="size-3.5" />
            Risk settings
          </Link>
        </Button>
      </div>

      <PositionSizer />

      <RiskSummary />
    </div>
  );
}

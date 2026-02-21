"use client";

import { useState } from "react";
import { TradePlanForm } from "@/components/dashboard/TradePlanForm";
import { TradePlansList } from "@/components/dashboard/TradePlansList";
import { Button } from "@/components/ui/button";

export default function PlansPage() {
  const [showForm, setShowForm] = useState(false);
  const [listKey, setListKey] = useState(0);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Trade plans</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Plan trades with entry, target, stop loss and risk calculations
          </p>
        </div>
        {!showForm && (
          <Button onClick={() => setShowForm(true)}>+ New plan</Button>
        )}
      </div>

      {showForm && (
        <TradePlanForm
          onSaved={() => {
            setShowForm(false);
            setListKey((k) => k + 1);
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <TradePlansList key={listKey} />
    </div>
  );
}

"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { TradeJournalForm } from "@/components/dashboard/TradeJournalForm";
import { TradeJournalList } from "@/components/dashboard/TradeJournalList";

export default function JournalPage() {
  const [showForm, setShowForm] = useState(false);
  const [listKey, setListKey] = useState(0);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">
            Trade journal
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            Post-trade analysis and lessons learned
          </p>
        </div>
        {!showForm && (
          <Button onClick={() => setShowForm(true)}>+ New entry</Button>
        )}
      </div>

      {showForm && (
        <TradeJournalForm
          tradePlanSymbol="Manual"
          onSaved={() => {
            setShowForm(false);
            setListKey((k) => k + 1);
          }}
          onCancel={() => setShowForm(false)}
        />
      )}

      <TradeJournalList key={listKey} />
    </div>
  );
}

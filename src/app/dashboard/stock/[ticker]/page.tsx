"use client";

import { use, useCallback, useState } from "react";
import { StockPageHeader } from "@/components/dashboard/StockPageHeader";
import { StockPageContent } from "@/components/dashboard/StockPageContent";

type StockOption = { id: string; ticker: string; name: string; sector: string; lastPrice?: number | null };

export default function StockPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker: rawTicker } = use(params);
  const [stocks, setStocks] = useState<StockOption[] | null>(null);

  const loadStocks = useCallback(() => {
    fetch("/api/stocks")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.stocks) {
          setStocks(res.data.stocks);
        }
      })
      .catch(() => {});
  }, []);

  const ticker = rawTicker ?? "";
  const normalizedTicker = ticker.trim().toUpperCase().replace(".KA", "");

  if (!normalizedTicker) {
    return (
      <div className="space-y-6">
        <p className="text-muted-foreground">Invalid or missing ticker.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <StockPageHeader
        ticker={normalizedTicker}
        stocks={stocks}
        onStocksLoad={loadStocks}
      />
      <StockPageContent ticker={normalizedTicker} />
    </div>
  );
}

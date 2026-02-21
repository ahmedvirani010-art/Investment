"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronLeft } from "lucide-react";

type StockOption = { id: string; ticker: string; name: string; sector: string; lastPrice?: number | null };

export function StockPageHeader({
  ticker,
  stocks,
  onStocksLoad,
}: {
  ticker: string;
  stocks: StockOption[] | null;
  onStocksLoad: () => void;
}) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const [livePrice, setLivePrice] = useState<number | null>(null);
  const [livePriceLoading, setLivePriceLoading] = useState(false);

  const normalizedTicker = ticker.trim().toUpperCase().replace(".KA", "");
  const current = stocks?.find((s) => s.ticker === normalizedTicker);

  const fetchLivePrice = useCallback(() => {
    if (!normalizedTicker) return;
    setLivePriceLoading(true);
    setLivePrice(null);
    fetch(`/api/price?ticker=${encodeURIComponent(normalizedTicker)}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.price != null) setLivePrice(res.data.price);
      })
      .finally(() => setLivePriceLoading(false));
  }, [normalizedTicker]);

  useEffect(() => {
    setMounted(true);
    if (stocks === null) onStocksLoad();
  }, [stocks, onStocksLoad]);

  // Fetch current price on mount and when ticker changes
  useEffect(() => {
    if (normalizedTicker) fetchLivePrice();
  }, [normalizedTicker, fetchLivePrice]);

  const handleSymbolChange = (value: string) => {
    if (value && value !== normalizedTicker) {
      router.push(`/dashboard/stock/${value}`);
    }
  };

  if (!mounted) {
    return (
      <Card>
        <CardContent className="pt-6">
          <Skeleton className="h-8 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-wrap items-center gap-4">
          <Link
            href="/dashboard"
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ChevronLeft className="size-4" />
            Dashboard
          </Link>
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-baseline gap-2">
              <h1 className="text-2xl font-semibold text-foreground">
                {normalizedTicker}
              </h1>
              {current && (
                <>
                  <span className="text-muted-foreground">—</span>
                  <span className="text-muted-foreground truncate">
                    {current.name}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {current.sector}
                  </span>
                </>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              {livePriceLoading && livePrice == null && current?.lastPrice == null ? (
                <Skeleton className="h-7 w-24" />
              ) : livePrice != null || current?.lastPrice != null ? (
                <>
                  <p className="text-lg font-medium tabular-nums">
                    ₨ {(livePrice ?? current?.lastPrice ?? 0).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </p>
                  {livePrice != null && (
                    <span className="text-xs text-muted-foreground">Live</span>
                  )}
                </>
              ) : (
                <p className="text-sm text-muted-foreground">Price unavailable</p>
              )}
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs text-muted-foreground"
                disabled={livePriceLoading}
                onClick={fetchLivePrice}
              >
                {livePriceLoading ? "…" : "Refresh price"}
              </Button>
            </div>
          </div>
          {stocks && stocks.length > 0 && (
            <Select
              value={normalizedTicker}
              onValueChange={handleSymbolChange}
            >
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Switch symbol" />
              </SelectTrigger>
              <SelectContent>
                {stocks.map((s) => (
                  <SelectItem key={s.id} value={s.ticker}>
                    {s.ticker}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

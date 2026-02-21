"use client";

import { FundamentalResultCard } from "@/components/dashboard/stock-page/FundamentalResultCard";
import { TechnicalResultCard } from "@/components/dashboard/stock-page/TechnicalResultCard";
import { StockNewsCard } from "@/components/dashboard/stock-page/StockNewsCard";
import { StockAnnouncementsCard } from "@/components/dashboard/stock-page/StockAnnouncementsCard";
import { StockAnomaliesCard } from "@/components/dashboard/stock-page/StockAnomaliesCard";
import { StockPositionCard } from "@/components/dashboard/stock-page/StockPositionCard";

export function StockPageContent({ ticker }: { ticker: string }) {
  return (
    <div className="space-y-8">
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <FundamentalResultCard ticker={ticker} />
          <TechnicalResultCard ticker={ticker} />
        </div>
        <div className="space-y-6">
          <StockPositionCard ticker={ticker} />
          <StockNewsCard ticker={ticker} />
          <StockAnnouncementsCard ticker={ticker} />
          <StockAnomaliesCard ticker={ticker} />
        </div>
      </div>
    </div>
  );
}

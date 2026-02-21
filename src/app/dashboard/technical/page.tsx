import { TechnicalAnalysis } from "@/components/dashboard/TechnicalAnalysis";

export default function TechnicalPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Technical Analysis
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Indicators and signals from PSXTechnicalAgent (RSI, MACD, SMA,
          Bollinger, etc.) for PSX stocks.
        </p>
      </div>
      <TechnicalAnalysis />
    </div>
  );
}

import { LiquidityTable } from "@/components/dashboard/LiquidityTable";

export default function LiquidityPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Liquidity Analysis
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Screen PSX stocks by average daily traded value (PSXLiquidityScreener)
        </p>
      </div>
      <LiquidityTable />
    </div>
  );
}

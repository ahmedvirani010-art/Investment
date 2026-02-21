import { FundamentalAnalysis } from "@/components/dashboard/FundamentalAnalysis";

export default function FundamentalPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Fundamental Analysis
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Score PSX stocks by valuation, financial health, growth, and momentum
          using PSXFundamentalAgent.
        </p>
      </div>
      <FundamentalAnalysis />
    </div>
  );
}

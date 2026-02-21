import { HMMRegimeAnalysis } from "@/components/dashboard/HMMRegimeAnalysis";

export default function NASDAQHMMRegimePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          NASDAQ HMM Regimes
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Hidden Markov Model (Gaussian HMM) on returns, range, and volume change
          for NASDAQ Composite (^IXIC). Same features as the generic HMM regime
          engine.
        </p>
      </div>
      <HMMRegimeAnalysis
        apiPath="/api/analysis/nasdaq-hmm-regime"
        defaultSymbol="^IXIC"
        defaultPeriod="730d"
        defaultInterval="1d"
        defaultNComponents={7}
        title="NASDAQ HMM Regimes"
        description="Gaussian HMM regime detection for NASDAQ Composite (^IXIC). Same features: returns, range, volume change."
      />
    </div>
  );
}

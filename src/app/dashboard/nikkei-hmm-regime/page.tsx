import { HMMRegimeAnalysis } from "@/components/dashboard/HMMRegimeAnalysis";

export default function NIKKEIHMMRegimePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          NIKKEI HMM Regimes
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Hidden Markov Model (Gaussian HMM) on returns, range, and volume change
          for Nikkei 225 (^N225). Same features as the generic HMM regime
          engine.
        </p>
      </div>
      <HMMRegimeAnalysis
        apiPath="/api/analysis/nikkei-hmm-regime"
        defaultSymbol="^N225"
        defaultPeriod="730d"
        defaultInterval="1d"
        defaultNComponents={7}
        title="NIKKEI HMM Regimes"
        description="Gaussian HMM regime detection for Nikkei 225 (^N225). Same features: returns, range, volume change."
      />
    </div>
  );
}

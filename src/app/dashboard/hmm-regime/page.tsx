import {
  HMMRegimeAnalysis,
  HMM_ASSET_PRESETS,
} from "@/components/dashboard/HMMRegimeAnalysis";
import { HMMRegimeBacktest } from "@/components/dashboard/HMMRegimeBacktest";

export default function HMMRegimePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          HMM Market Regimes
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Hidden Markov Model (7-state Gaussian HMM) for Bitcoin, Gold, Crude
          Oil, Silver, NASDAQ, NIKKEI, and S&P 500. Select an asset above or
          enter any yfinance symbol (e.g. LUCK.PK).
        </p>
      </div>
      <HMMRegimeAnalysis assetPresets={HMM_ASSET_PRESETS} />
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-2">
          HMM Regime Backtest
        </h2>
        <p className="text-muted-foreground text-sm mb-4">
          Strategy: enter when regime is Bull and at least 7 of 8 technical
          confirmations hold; exit when regime flips to Bear. 48h cooldown, 1.25x
          leverage on PnL.
        </p>
        <HMMRegimeBacktest />
      </div>
    </div>
  );
}

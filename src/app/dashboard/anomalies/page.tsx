import { AnomalyAlert } from "@/components/dashboard/AnomalyAlert";

export default function AnomaliesPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Anomaly Detection
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Detect unusual trading patterns (volume, price, gaps, volatility)
        </p>
      </div>
      <AnomalyAlert />
    </div>
  );
}

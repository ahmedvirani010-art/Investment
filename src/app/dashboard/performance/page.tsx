import { PerformanceChart } from "@/components/dashboard/PerformanceChart";

export default function PerformancePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Performance
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Portfolio value over time (AccountSnapshot history)
        </p>
      </div>
      <PerformanceChart />
    </div>
  );
}

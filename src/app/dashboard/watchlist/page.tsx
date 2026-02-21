import { WatchlistContent } from "@/components/dashboard/WatchlistContent";

export default function WatchlistPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Watchlist</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Track stocks you’re interested in with optional notes and target prices
        </p>
      </div>
      <WatchlistContent />
    </div>
  );
}

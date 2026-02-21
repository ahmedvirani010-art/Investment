import { NewsDashboard } from "@/components/dashboard/NewsDashboard";

export default function NewsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">News</h1>
        <p className="text-muted-foreground text-sm mt-1">
          PSX news: fetch from sources or view recent by symbol and macro.
        </p>
      </div>
      <NewsDashboard />
    </div>
  );
}

import { AnnouncementsDashboard } from "@/components/dashboard/AnnouncementsDashboard";

export default function AnnouncementsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">
          Announcements
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Official PSX company announcements: dividends, results, board meetings, and material info
        </p>
      </div>
      <AnnouncementsDashboard />
    </div>
  );
}

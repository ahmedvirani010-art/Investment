"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type AnnouncementDto = {
  announcement_id: string;
  symbol: string;
  announcement_date: string;
  category?: string | null;
  subcategory?: string | null;
  materiality_tier?: number | null;
  title: string;
  description?: string | null;
  attachment_url?: string | null;
  source_url: string;
  dividend_amount?: number | null;
  dividend_type?: string | null;
  profit_change_pct?: number | null;
};

const tierLabels: Record<number, string> = {
  1: "Critical",
  2: "Material",
  3: "Informational",
};

const tierVariant: Record<number, "destructive" | "default" | "secondary" | "outline"> = {
  1: "destructive",
  2: "default",
  3: "secondary",
};

export function StockAnnouncementsCard({ ticker }: { ticker: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [announcements, setAnnouncements] = useState<AnnouncementDto[]>([]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setAnnouncements([]);
    const params = new URLSearchParams({
      action: "list",
      days: "7",
      symbols: ticker,
    });
    fetch(`/api/analysis/announcements?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.announcements) {
          setAnnouncements(Array.isArray(res.announcements) ? res.announcements : []);
        } else {
          setError(res.error ?? "Failed to load announcements");
        }
      })
      .catch((e) => {
        setError(e.message ?? "Request failed");
      })
      .finally(() => setLoading(false));
  }, [ticker]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Announcements</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full mt-2" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle>Announcements</CardTitle>
        </CardHeader>
        <CardContent className="text-destructive">{error}</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Announcements</CardTitle>
        <p className="text-sm text-muted-foreground">Last 7 days</p>
      </CardHeader>
      <CardContent>
        {announcements.length === 0 ? (
          <p className="text-sm text-muted-foreground">No announcements for this symbol.</p>
        ) : (
          <ul className="space-y-3">
            {announcements.map((a) => {
              const tier = a.materiality_tier ?? 3;
              return (
                <li key={a.announcement_id} className="border-b border-border pb-3 last:border-0 last:pb-0">
                  <a
                    href={a.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline font-medium block"
                  >
                    {a.title || "—"}
                  </a>
                  <div className="flex flex-wrap items-center gap-2 mt-1 text-sm text-muted-foreground">
                    <span>
                      {a.announcement_date
                        ? new Date(a.announcement_date).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })
                        : "—"}
                    </span>
                    {a.category && <span>· {a.category}</span>}
                    <Badge variant={tierVariant[tier] ?? "outline"} className="text-xs">
                      {tierLabels[tier] ?? `Tier ${tier}`}
                    </Badge>
                    {a.dividend_amount != null && <span>· Div {a.dividend_amount}% {a.dividend_type ?? ""}</span>}
                    {a.profit_change_pct != null && (
                      <span>· Profit {a.profit_change_pct > 0 ? "+" : ""}{a.profit_change_pct}%</span>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type NewsArticleDto = {
  article_id: string;
  title: string;
  url: string;
  source: string;
  published_date: string;
  mentioned_symbols?: string[];
  sentiment_label?: string | null;
  summary?: string;
};

export function StockNewsCard({ ticker }: { ticker: string }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [articles, setArticles] = useState<NewsArticleDto[]>([]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setArticles([]);
    const params = new URLSearchParams({
      mode: "symbols",
      symbols: ticker,
      days: "7",
    });
    fetch(`/api/analysis/news?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data && typeof res.data === "object" && res.data[ticker]) {
          setArticles(Array.isArray(res.data[ticker]) ? res.data[ticker] : []);
        } else {
          setError(res.error ?? "Failed to load news");
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
          <CardTitle>News</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full mt-2" />
          <Skeleton className="h-20 w-full mt-2" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle>News</CardTitle>
        </CardHeader>
        <CardContent className="text-destructive">{error}</CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>News</CardTitle>
        <p className="text-sm text-muted-foreground">Last 7 days</p>
      </CardHeader>
      <CardContent>
        {articles.length === 0 ? (
          <p className="text-sm text-muted-foreground">No news for this symbol.</p>
        ) : (
          <ul className="space-y-3">
            {articles.map((a) => (
              <li key={a.article_id} className="border-b border-border pb-3 last:border-0 last:pb-0">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline font-medium block"
                >
                  {a.title}
                </a>
                <div className="flex flex-wrap items-center gap-2 mt-1 text-sm text-muted-foreground">
                  <span>{a.source}</span>
                  <span>·</span>
                  <span>
                    {a.published_date
                      ? new Date(a.published_date).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" })
                      : "—"}
                  </span>
                  {a.sentiment_label && (
                    <>
                      <span>·</span>
                      <Badge variant="outline" className="text-xs">
                        {a.sentiment_label}
                      </Badge>
                    </>
                  )}
                </div>
                {a.summary && <p className="text-sm mt-1 line-clamp-2">{a.summary}</p>}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

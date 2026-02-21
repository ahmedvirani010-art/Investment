"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

type NewsArticleDto = {
  article_id: string;
  title: string;
  url: string;
  source: string;
  published_date: string;
  fetched_date?: string;
  mentioned_symbols?: string[];
  primary_symbol?: string | null;
  sentiment_label?: string | null;
  sentiment_score?: number | null;
  macro_category?: string | null;
  relevance_score?: number;
  is_macro_news?: boolean;
  summary?: string;
};

type FetchSummary = {
  total_fetched: number;
  stock_news: number;
  macro_news: number;
  new_articles: number;
  duplicates: number;
  symbols_mentioned: string[];
  macro_categories: string[];
};

function ArticleRow({ a }: { a: NewsArticleDto }) {
  return (
    <TableRow>
      <TableCell className="font-medium max-w-[280px]">
        <a
          href={a.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline truncate block"
        >
          {a.title}
        </a>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">{a.source}</TableCell>
      <TableCell className="text-sm">
        {a.published_date ? new Date(a.published_date).toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" }) : "-"}
      </TableCell>
      <TableCell>
        {a.mentioned_symbols?.length ? (
          <span className="text-sm">{a.mentioned_symbols.slice(0, 5).join(", ")}</span>
        ) : (
          <span className="text-muted-foreground">-</span>
        )}
      </TableCell>
      <TableCell>
        {a.sentiment_label ? (
          <Badge variant="outline" className="text-xs">
            {a.sentiment_label}
          </Badge>
        ) : (
          "-"
        )}
      </TableCell>
      <TableCell>
        {a.macro_category ? (
          <Badge variant="secondary" className="text-xs">
            {a.macro_category}
          </Badge>
        ) : (
          "-"
        )}
      </TableCell>
    </TableRow>
  );
}

export function NewsDashboard() {
  const [mode, setMode] = useState<"fetch" | "recent" | "symbols" | "macro">("recent");
  const [hours, setHours] = useState(24);
  const [fetchHours, setFetchHours] = useState(48);
  const [limit, setLimit] = useState(50);
  const [symbols, setSymbols] = useState("LUCK, PSO, HBL, OGDC");
  const [days, setDays] = useState(7);
  const [macroHours, setMacroHours] = useState(48);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{
    success: boolean;
    data?: Record<string, unknown>;
    timestamp?: string;
  } | null>(null);
  const [errorDetails, setErrorDetails] = useState<string | null>(null);

  const setModeAndClearResult = (v: string) => {
    setMode(v as typeof mode);
    setResult(null);
    setError(null);
    setErrorDetails(null);
  };

  const runFetch = () => {
    setLoading(true);
    setError(null);
    setResult(null);
    const params = new URLSearchParams({ mode: "fetch", hours: String(fetchHours) });
    fetch(`/api/analysis/news?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          setResult(res);
          setErrorDetails(null);
        } else {
          setError(res.error ?? "Fetch failed");
          setErrorDetails(res.details ?? null);
        }
      })
      .catch((e) => {
        setError(e.message ?? "Request failed");
        setErrorDetails(null);
      })
      .finally(() => setLoading(false));
  };

  const runRecent = () => {
    setLoading(true);
    setError(null);
    setResult(null);
    const params = new URLSearchParams({
      mode: "recent",
      hours: String(hours),
      limit: String(limit),
    });
    fetch(`/api/analysis/news?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          setResult(res);
          setErrorDetails(null);
        } else {
          setError(res.error ?? "Load failed");
          setErrorDetails(res.details ?? null);
        }
      })
      .catch((e) => {
        setError(e.message ?? "Request failed");
        setErrorDetails(null);
      })
      .finally(() => setLoading(false));
  };

  const runSymbols = () => {
    setLoading(true);
    setError(null);
    setResult(null);
    const params = new URLSearchParams({
      mode: "symbols",
      symbols: symbols.trim(),
      days: String(days),
    });
    fetch(`/api/analysis/news?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          setResult(res);
          setErrorDetails(null);
        } else {
          setError(res.error ?? "Load failed");
          setErrorDetails(res.details ?? null);
        }
      })
      .catch((e) => {
        setError(e.message ?? "Request failed");
        setErrorDetails(null);
      })
      .finally(() => setLoading(false));
  };

  const runMacro = () => {
    setLoading(true);
    setError(null);
    setResult(null);
    const params = new URLSearchParams({ mode: "macro", hours: String(macroHours) });
    fetch(`/api/analysis/news?${params}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          setResult(res);
          setErrorDetails(null);
        } else {
          setError(res.error ?? "Load failed");
          setErrorDetails(res.details ?? null);
        }
      })
      .catch((e) => {
        setError(e.message ?? "Request failed");
        setErrorDetails(null);
      })
      .finally(() => setLoading(false));
  };

  const fetchData = result?.data as
    | { summary: FetchSummary; recent_articles: NewsArticleDto[] }
    | undefined;
  const recentData = result?.data as { articles: NewsArticleDto[] } | undefined;
  const symbolsData = result?.data as Record<string, NewsArticleDto[]> | undefined;
  const macroData = result?.data as Record<string, NewsArticleDto[]> | undefined;

  return (
    <div className="space-y-6">
      <Tabs
        value={mode}
        onValueChange={setModeAndClearResult}
      >
        <Card>
          <CardHeader>
            <CardTitle>Mode</CardTitle>
            <p className="text-sm text-muted-foreground">
              Fetch from RSS and process, or view stored news by recent / symbols / macro.
              Requires Python deps from project root: <code className="text-xs bg-muted px-1 rounded">pip install -r requirements.txt</code> (or <code className="text-xs bg-muted px-1 rounded">py -m pip install -r requirements.txt</code> on Windows).
            </p>
          </CardHeader>
          <CardContent>
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="fetch">Fetch latest</TabsTrigger>
              <TabsTrigger value="recent">Recent</TabsTrigger>
              <TabsTrigger value="symbols">By symbols</TabsTrigger>
              <TabsTrigger value="macro">Macro summary</TabsTrigger>
            </TabsList>

            <TabsContent value="fetch" className="space-y-4 pt-4">
              <p className="text-sm text-muted-foreground">
                This may take a few minutes. Fetches from RSS, processes (symbol match, sentiment, macro), and stores.
              </p>
              <div className="flex flex-wrap items-end gap-4">
                <div className="space-y-2">
                  <Label>Hours lookback</Label>
                  <Input
                    type="number"
                    min={12}
                    max={168}
                    value={fetchHours}
                    onChange={(e) => setFetchHours(Number(e.target.value))}
                    className="w-28"
                  />
                </div>
                <Button onClick={runFetch} disabled={loading}>
                  {loading ? "Fetching..." : "Fetch & process"}
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="recent" className="space-y-4 pt-4">
              <div className="flex flex-wrap items-end gap-4">
                <div className="space-y-2">
                  <Label>Hours</Label>
                  <Input
                    type="number"
                    min={1}
                    max={168}
                    value={hours}
                    onChange={(e) => setHours(Number(e.target.value))}
                    className="w-28"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Limit</Label>
                  <Input
                    type="number"
                    min={1}
                    max={500}
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    className="w-28"
                  />
                </div>
                <Button onClick={runRecent} disabled={loading}>
                  {loading ? "Loading..." : "Load"}
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="symbols" className="space-y-4 pt-4">
              <div className="flex flex-wrap items-end gap-4">
                <div className="space-y-2 min-w-[200px]">
                  <Label>Symbols (comma-separated)</Label>
                  <Input
                    placeholder="e.g. LUCK, PSO, HBL"
                    value={symbols}
                    onChange={(e) => setSymbols(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Days</Label>
                  <Input
                    type="number"
                    min={1}
                    max={30}
                    value={days}
                    onChange={(e) => setDays(Number(e.target.value))}
                    className="w-24"
                  />
                </div>
                <Button onClick={runSymbols} disabled={loading || !symbols.trim()}>
                  {loading ? "Loading..." : "Load"}
                </Button>
              </div>
            </TabsContent>

            <TabsContent value="macro" className="space-y-4 pt-4">
              <div className="flex flex-wrap items-end gap-4">
                <div className="space-y-2">
                  <Label>Hours</Label>
                  <Input
                    type="number"
                    min={12}
                    max={168}
                    value={macroHours}
                    onChange={(e) => setMacroHours(Number(e.target.value))}
                    className="w-28"
                  />
                </div>
                <Button onClick={runMacro} disabled={loading}>
                  {loading ? "Loading..." : "Load"}
                </Button>
              </div>
            </TabsContent>
          </CardContent>
        </Card>
      </Tabs>

      {error && (
        <Card>
          <CardContent className="py-4 space-y-2">
            <p className="text-destructive">{error}</p>
            {errorDetails && (
              <pre className="text-xs text-muted-foreground bg-muted p-3 rounded overflow-auto max-h-40">
                {errorDetails}
              </pre>
            )}
          </CardContent>
        </Card>
      )}

      {loading && (
        <Card>
          <CardContent className="py-8">
            <Skeleton className="h-64 w-full" />
          </CardContent>
        </Card>
      )}

      {result && !loading && mode === "fetch" && fetchData && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Fetch summary</CardTitle>
              <p className="text-sm text-muted-foreground">
                Total fetched: {fetchData.summary?.total_fetched} · New: {fetchData.summary?.new_articles} ·
                Duplicates: {fetchData.summary?.duplicates} · Stock news: {fetchData.summary?.stock_news} ·
                Macro: {fetchData.summary?.macro_news}
                {fetchData.summary?.symbols_mentioned?.length ? ` · Symbols: ${fetchData.summary.symbols_mentioned.slice(0, 15).join(", ")}${fetchData.summary.symbols_mentioned.length > 15 ? "…" : ""}` : ""}
              </p>
            </CardHeader>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Recent articles</CardTitle>
            </CardHeader>
            <CardContent>
              {!fetchData.recent_articles?.length ? (
                <p className="text-muted-foreground py-4">No recent articles.</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Title</TableHead>
                      <TableHead>Source</TableHead>
                      <TableHead>Published</TableHead>
                      <TableHead>Symbols</TableHead>
                      <TableHead>Sentiment</TableHead>
                      <TableHead>Macro</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {fetchData.recent_articles.map((a) => (
                      <ArticleRow key={a.article_id} a={a} />
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {result && !loading && mode === "recent" && recentData && (
        <Card>
          <CardHeader>
            <CardTitle>Recent articles</CardTitle>
            <p className="text-sm text-muted-foreground">
              {recentData.articles?.length ?? 0} articles
            </p>
          </CardHeader>
          <CardContent>
            {!recentData.articles?.length ? (
              <p className="text-muted-foreground py-4">No articles in this period.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Title</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Published</TableHead>
                    <TableHead>Symbols</TableHead>
                    <TableHead>Sentiment</TableHead>
                    <TableHead>Macro</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentData.articles.map((a) => (
                    <ArticleRow key={a.article_id} a={a} />
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {result && !loading && mode === "symbols" && symbolsData && (
        <Card>
          <CardHeader>
            <CardTitle>News by symbol</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {Object.keys(symbolsData).length === 0 ? (
              <p className="text-muted-foreground py-4">No news found for these symbols.</p>
            ) : (
              Object.entries(symbolsData).map(([symbol, articles]) => (
                <div key={symbol}>
                  <h3 className="font-medium mb-2">{symbol} ({articles.length})</h3>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Title</TableHead>
                        <TableHead>Source</TableHead>
                        <TableHead>Published</TableHead>
                        <TableHead>Symbols</TableHead>
                        <TableHead>Sentiment</TableHead>
                        <TableHead>Macro</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {articles.map((a) => (
                        <ArticleRow key={a.article_id} a={a} />
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      )}

      {result && !loading && mode === "macro" && macroData && (
        <Card>
          <CardHeader>
            <CardTitle>Macro news by category</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {Object.keys(macroData).length === 0 ? (
              <p className="text-muted-foreground py-4">No macro news in this period.</p>
            ) : (
              Object.entries(macroData).map(([category, articles]) => (
                <div key={category}>
                  <h3 className="font-medium mb-2">{category} ({articles.length})</h3>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Title</TableHead>
                        <TableHead>Source</TableHead>
                        <TableHead>Published</TableHead>
                        <TableHead>Symbols</TableHead>
                        <TableHead>Sentiment</TableHead>
                        <TableHead>Macro</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {articles.map((a) => (
                        <ArticleRow key={a.article_id} a={a} />
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      )}

      {!result && !loading && !error && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            Choose a mode, set parameters, and click Load or Fetch to see news.
          </CardContent>
        </Card>
      )}
    </div>
  );
}

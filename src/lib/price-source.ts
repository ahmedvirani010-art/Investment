/**
 * Live price source for PSX stocks.
 * Primary: Yahoo Finance (yahoo-finance2).
 * Fallbacks: Brackly, PSX portal scrape, then local price store (price_data/prices.db from Python).
 */

const PSX_SUFFIX = ".KA";
const BRACKLY_API_BASE = "https://capital.brackly.com";
const PSX_PORTAL_BASE = "https://dps.psx.com.pk";

function toYahooSymbol(ticker: string): string {
  const t = ticker.trim().toUpperCase().replace(/\.KA$/i, "");
  return t ? `${t}${PSX_SUFFIX}` : "";
}

function normalizeTicker(ticker: string): string {
  return ticker.trim().toUpperCase().replace(/\.KA$/i, "");
}

export type QuoteResult = { ticker: string; price: number | null; error?: string; source?: string };

let client: { quote: (symbol: string) => Promise<unknown> } | null = null;
let clientPromise: Promise<{ quote: (symbol: string) => Promise<unknown> }> | null = null;

async function getClient(): Promise<{ quote: (symbol: string) => Promise<unknown> }> {
  if (client) return client;
  if (!clientPromise) {
    clientPromise = (async () => {
      const mod = await import("yahoo-finance2");
      const YahooFinance = mod.default;
      if (typeof YahooFinance !== "function" && typeof (YahooFinance as { new (): unknown }) !== "function") {
        throw new Error("yahoo-finance2: invalid export");
      }
      client = new (YahooFinance as new () => { quote: (s: string) => Promise<unknown> })();
      return client;
    })();
  }
  return clientPromise;
}

function priceFromQuote(quote: unknown): number | null {
  if (quote == null || typeof quote !== "object") return null;
  const q = quote as Record<string, unknown>;
  const candidates = [
    q.regularMarketPrice,
    q.regularMarketPreviousClose,
    q.previousClose,
    q.open,
  ];
  for (const v of candidates) {
    if (typeof v === "number" && Number.isFinite(v)) return v;
    if (typeof v === "string") {
      const n = parseFloat(v);
      if (Number.isFinite(n)) return n;
    }
  }
  return null;
}

/** Fetch from Brackly Capital API. Requires BRACKLY_API_KEY. */
async function fetchBracklyPrice(ticker: string): Promise<QuoteResult> {
  const key = process.env.BRACKLY_API_KEY?.trim();
  if (!key) return { ticker: normalizeTicker(ticker), price: null, error: "BRACKLY_API_KEY not set" };

  const sym = normalizeTicker(ticker);
  if (!sym) return { ticker: ticker.trim(), price: null, error: "Invalid ticker" };

  const url = `${BRACKLY_API_BASE}/api/price?symbol=${encodeURIComponent(sym)}`;
  try {
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${key}` },
      signal: AbortSignal.timeout(10000),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const msg = (data?.message ?? data?.error ?? res.statusText) || "Brackly request failed";
      return { ticker: sym, price: null, error: msg };
    }
    const price = typeof data?.price === "number" && Number.isFinite(data.price)
      ? data.price
      : typeof data?.price === "string"
        ? parseFloat(data.price)
        : null;
    if (price != null && Number.isFinite(price)) {
      return { ticker: sym, price, source: "brackly" };
    }
    return { ticker: sym, price: null, error: "No price in response" };
  } catch (e) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return { ticker: sym, price: null, error: message };
  }
}

/**
 * Best-effort scrape of PSX data portal for a symbol's price.
 * Portal may serve equity data in HTML; if not (e.g. JS-only), returns null.
 */
async function fetchPSXPortalPrice(ticker: string): Promise<QuoteResult> {
  const sym = normalizeTicker(ticker);
  if (!sym) return { ticker: ticker.trim(), price: null, error: "Invalid ticker" };

  const urlsToTry = [
    `${PSX_PORTAL_BASE}/`,
    `${PSX_PORTAL_BASE}/sector-summary`,
    `${PSX_PORTAL_BASE}/historical`,
  ];

  for (const url of urlsToTry) {
    try {
      const res = await fetch(url, {
        headers: { "User-Agent": "Mozilla/5.0 (compatible; PSX-Dashboard/1.0)" },
        signal: AbortSignal.timeout(12000),
      });
      const html = await res.text();
      if (!html || html.length < 500) continue;

      // Look for ticker as whole word then a number that could be price (e.g. 123.45 or 1,234.56)
      const tickerEsc = sym.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const pricePattern = new RegExp(
        `(?:^|[^a-zA-Z0-9])${tickerEsc}(?:[^0-9]*?)([0-9]{1,3}(?:,[0-9]{3})*(?:\\.[0-9]{2})?|[0-9]+\\.[0-9]{2})(?:[^0-9]|$)`,
        "im"
      );
      const m = html.match(pricePattern);
      if (m?.[1]) {
        const price = parseFloat(m[1].replace(/,/g, ""));
        if (Number.isFinite(price) && price > 0 && price < 1e8) {
          return { ticker: sym, price, source: "psx_portal" };
        }
      }
    } catch {
      // next URL
    }
  }

  return { ticker: sym, price: null, error: "PSX portal: no price found" };
}

/**
 * Read latest close from local price store (price_data/prices.db) via Python.
 * Use when Yahoo/Brackly/PSX scrape all fail; run: python psx_price_store.py (or bulk_update) to populate.
 */
async function getPriceFromLocalStore(ticker: string): Promise<QuoteResult> {
  const sym = normalizeTicker(ticker);
  if (!sym) return { ticker: ticker.trim(), price: null, error: "Invalid ticker" };

  const pythonCmd = process.env.PYTHON_PATH ?? (process.platform === "win32" ? "py" : "python3");
  const script = [
    "import sqlite3, os, sys",
    "db = os.path.join(os.getcwd(), 'price_data', 'prices.db')",
    "if not os.path.isfile(db): sys.exit(1)",
    "c = sqlite3.connect(db)",
    "r = c.execute('SELECT close FROM daily_prices WHERE symbol=? ORDER BY date DESC LIMIT 1', (sys.argv[1],)).fetchone()",
    "c.close()",
    "print(r[0] if r and r[0] is not None else '', end='')",
  ].join("; ");

  return new Promise((resolve) => {
    import("child_process").then(({ spawn }) => {
    const proc = spawn(pythonCmd, ["-c", script, sym], {
      cwd: process.cwd(),
      timeout: 8000,
    });
    let out = "";
    let err = "";
    proc.stdout?.on("data", (ch: Buffer) => { out += ch.toString(); });
    proc.stderr?.on("data", (ch: Buffer) => { err += ch.toString(); });
    proc.on("close", (code) => {
      if (code !== 0) {
        resolve({ ticker: sym, price: null, error: "Local store: no price" });
        return;
      }
      const s = out.trim();
      const price = s ? parseFloat(s) : NaN;
      if (Number.isFinite(price) && price > 0) {
        resolve({ ticker: sym, price, source: "local_store" });
      } else {
        resolve({ ticker: sym, price: null, error: "Local store: no price" });
      }
    });
    proc.on("error", () => resolve({ ticker: sym, price: null, error: "Local store: no price" }));
    }).catch(() => resolve({ ticker: sym, price: null, error: "Local store: no price" }));
  });
}

/**
 * Fetch current/latest price for a single PSX ticker.
 * Order: Yahoo -> Brackly (if key set) -> PSX portal scrape -> local price store.
 */
export async function getQuote(ticker: string): Promise<QuoteResult> {
  const symbol = toYahooSymbol(ticker);
  const baseTicker = normalizeTicker(ticker);
  if (!baseTicker) {
    return { ticker: ticker.trim(), price: null, error: "Invalid ticker" };
  }

  let yahooError: string | undefined;

  // 1) Yahoo
  try {
    if (symbol) {
      const yf = await getClient();
      const quote = await yf.quote(symbol);
      const price = priceFromQuote(quote);
      if (price != null) {
        return { ticker: baseTicker, price, source: "yahoo" };
      }
      yahooError = "No price returned";
    }
  } catch (e) {
    yahooError = e instanceof Error ? e.message : "Unknown error";
  }

  // 2) Fallback: Brackly (if BRACKLY_API_KEY is set)
  const brackly = await fetchBracklyPrice(ticker);
  if (brackly.price != null) return brackly;

  // 3) Fallback: PSX data portal scrape (best-effort when Yahoo fails)
  const psx = await fetchPSXPortalPrice(ticker);
  if (psx.price != null) return psx;

  // 4) Fallback: local price store (price_data/prices.db from Python psx_price_store)
  const local = await getPriceFromLocalStore(ticker);
  if (local.price != null) return local;

  return { ticker: baseTicker, price: null, error: yahooError ?? brackly.error ?? psx.error ?? local.error ?? "No price" };
}

const BATCH_DELAY_MS = 200;
const MAX_TICKERS_PER_BATCH = 50;

/**
 * Fetch prices for multiple tickers with simple rate limiting.
 */
export async function getQuotes(tickers: string[]): Promise<QuoteResult[]> {
  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const t of tickers) {
    const n = t.trim().toUpperCase().replace(/\.KA$/i, "");
    if (n && !seen.has(n)) {
      seen.add(n);
      normalized.push(n);
    }
  }
  const limited = normalized.slice(0, MAX_TICKERS_PER_BATCH);
  const results: QuoteResult[] = [];
  for (let i = 0; i < limited.length; i++) {
    if (i > 0) await new Promise((r) => setTimeout(r, BATCH_DELAY_MS));
    results.push(await getQuote(limited[i]));
  }
  return results;
}

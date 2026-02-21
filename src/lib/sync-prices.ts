import { prisma } from "@/lib/prisma";
import { getQuotes } from "@/lib/price-source";

export type SyncPricesResult = {
  updated: number;
  errors: Array<{ ticker: string; error: string }>;
  total: number;
};

export async function syncPrices(): Promise<SyncPricesResult> {
  const stocks = await prisma.stock.findMany({
    where: { isActive: true },
    select: { id: true, ticker: true },
    orderBy: { ticker: "asc" },
  });

  if (stocks.length === 0) {
    return { updated: 0, errors: [], total: 0 };
  }

  const tickers = stocks.map((s) => s.ticker);
  const results = await getQuotes(tickers);

  let updated = 0;
  const errors: Array<{ ticker: string; error: string }> = [];

  for (const r of results) {
    if (r.error) {
      errors.push({ ticker: r.ticker, error: r.error });
      continue;
    }
    if (r.price == null) {
      errors.push({ ticker: r.ticker, error: "No price returned" });
      continue;
    }
    try {
      await prisma.stock.updateMany({
        where: { ticker: r.ticker },
        data: { lastPrice: r.price },
      });
      updated++;
    } catch (e) {
      errors.push({
        ticker: r.ticker,
        error: e instanceof Error ? e.message : "Update failed",
      });
    }
  }

  return { updated, errors, total: stocks.length };
}

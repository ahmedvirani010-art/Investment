import { NextRequest, NextResponse } from "next/server";
import { getQuote, getQuotes } from "@/lib/price-source";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const ticker = searchParams.get("ticker")?.trim();
  const tickersParam = searchParams.get("tickers")?.trim();

  if (tickersParam) {
    const tickers = tickersParam.split(",").map((t) => t.trim()).filter(Boolean);
    if (tickers.length === 0) {
      return NextResponse.json(
        { success: false, error: "tickers must be a non-empty comma-separated list" },
        { status: 400 }
      );
    }
    try {
      const results = await getQuotes(tickers);
      return NextResponse.json({
        success: true,
        data: results.map((r) => ({
          ticker: r.ticker,
          price: r.price,
          error: r.error ?? undefined,
        })),
        timestamp: new Date().toISOString(),
      });
    } catch (e) {
      console.error("Error fetching quotes:", e);
      return NextResponse.json(
        {
          success: false,
          error: "Failed to fetch quotes",
          details: e instanceof Error ? e.message : "Unknown error",
        },
        { status: 500 }
      );
    }
  }

  if (!ticker) {
    return NextResponse.json(
      { success: false, error: "Query parameter ticker or tickers is required" },
      { status: 400 }
    );
  }

  try {
    const result = await getQuote(ticker);
    return NextResponse.json({
      success: true,
      data: {
        ticker: result.ticker,
        price: result.price,
        error: result.error ?? undefined,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (e) {
    console.error("Error fetching quote:", e);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch quote",
        details: e instanceof Error ? e.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

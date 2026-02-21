import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { PSX_STOCK_LIST } from "@/lib/psx-data";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const sector = searchParams.get("sector") ?? undefined;
    const limit = Math.min(parseInt(searchParams.get("limit") ?? "500", 10), 1000);
    const stocks = await prisma.stock.findMany({
      where: sector ? { sector } : undefined,
      orderBy: { ticker: "asc" },
      take: limit,
    });
    return NextResponse.json({
      success: true,
      data: { stocks, total: stocks.length },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching scripts:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch scripts", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { ticker, name, sector } = body as { ticker?: string; name?: string; sector?: string };
    const tickerTrim = ticker?.trim().toUpperCase();
    if (!tickerTrim || !name?.trim() || !sector?.trim()) {
      return NextResponse.json(
        { success: false, error: "ticker, name, and sector are required" },
        { status: 400 }
      );
    }
    const existing = await prisma.stock.findUnique({ where: { ticker: tickerTrim } });
    if (existing) {
      return NextResponse.json(
        { success: false, error: "Stock with this ticker already exists" },
        { status: 409 }
      );
    }
    const stock = await prisma.stock.create({
      data: {
        ticker: tickerTrim,
        name: name.trim(),
        sector: sector.trim(),
      },
    });
    return NextResponse.json({
      success: true,
      data: { stock: { id: stock.id, ticker: stock.ticker, name: stock.name, sector: stock.sector } },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error creating script:", error);
    return NextResponse.json(
      { success: false, error: "Failed to create script", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

/** Import PSX reference list: add only scripts that don't exist (by ticker) */
export async function PUT(request: NextRequest) {
  try {
    const existing = await prisma.stock.findMany({ select: { ticker: true } });
    const existingTickers = new Set(existing.map((s) => s.ticker.toUpperCase()));
    const toAdd = PSX_STOCK_LIST.filter(
      (s) => !existingTickers.has(s.ticker.toUpperCase())
    );
    if (toAdd.length === 0) {
      return NextResponse.json({
        success: true,
        data: { imported: 0, message: "All scripts already exist" },
        timestamp: new Date().toISOString(),
      });
    }
    let imported = 0;
    for (const s of toAdd) {
      try {
        await prisma.stock.create({
          data: {
            ticker: s.ticker.toUpperCase(),
            name: s.name,
            sector: s.sector,
          },
        });
        imported++;
        existingTickers.add(s.ticker.toUpperCase());
      } catch (e) {
        // skip duplicate if raced
      }
    }
    return NextResponse.json({
      success: true,
      data: { imported, total: PSX_STOCK_LIST.length },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error importing PSX list:", error);
    return NextResponse.json(
      { success: false, error: "Failed to import PSX list", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

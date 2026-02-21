import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  try {
    const stocks = await prisma.stock.findMany({
      where: { isActive: true },
      select: { id: true, ticker: true, name: true, sector: true, lastPrice: true },
      orderBy: { ticker: "asc" },
    });
    return NextResponse.json({
      success: true,
      data: { stocks },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching stocks:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch stocks",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

type PostBody = { ticker: string; name: string; sector: string };

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as PostBody;
    const { ticker, name, sector } = body;
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
    console.error("Error creating stock:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to create stock",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

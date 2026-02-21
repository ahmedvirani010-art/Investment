import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  try {
    const items = await prisma.watchlistItem.findMany({
      include: {
        stock: {
          select: { id: true, ticker: true, name: true, sector: true, lastPrice: true },
        },
      },
      orderBy: { createdAt: "desc" },
    });
    return NextResponse.json({
      success: true,
      data: { items },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching watchlist:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch watchlist",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

type PostBody = { stockId: string; notes?: string; targetPrice?: number };

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as PostBody;
    const { stockId, notes, targetPrice } = body;
    if (!stockId?.trim()) {
      return NextResponse.json(
        { success: false, error: "stockId is required" },
        { status: 400 }
      );
    }
    const stock = await prisma.stock.findUnique({ where: { id: stockId.trim() } });
    if (!stock) {
      return NextResponse.json(
        { success: false, error: "Stock not found" },
        { status: 404 }
      );
    }
    const existing = await prisma.watchlistItem.findUnique({
      where: { stockId: stock.id },
    });
    if (existing) {
      return NextResponse.json(
        { success: false, error: "Stock is already on the watchlist" },
        { status: 409 }
      );
    }
    const item = await prisma.watchlistItem.create({
      data: {
        stockId: stock.id,
        notes: notes?.trim() || null,
        targetPrice: targetPrice != null && !Number.isNaN(Number(targetPrice)) ? Number(targetPrice) : null,
      },
      include: {
        stock: {
          select: { id: true, ticker: true, name: true, sector: true, lastPrice: true },
        },
      },
    });
    return NextResponse.json({
      success: true,
      data: { item },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error adding to watchlist:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to add to watchlist",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

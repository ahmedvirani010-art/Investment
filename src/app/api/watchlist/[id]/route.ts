import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

type RouteParams = { params: Promise<{ id: string }> };

export async function DELETE(_request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;
    if (!id) {
      return NextResponse.json(
        { success: false, error: "Watchlist item id is required" },
        { status: 400 }
      );
    }
    const item = await prisma.watchlistItem.findUnique({ where: { id } });
    if (!item) {
      return NextResponse.json(
        { success: false, error: "Watchlist item not found" },
        { status: 404 }
      );
    }
    await prisma.watchlistItem.delete({ where: { id } });
    return NextResponse.json({
      success: true,
      data: { deleted: id },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error removing from watchlist:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to remove from watchlist",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

type PatchBody = { notes?: string; targetPrice?: number | null };

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params;
    if (!id) {
      return NextResponse.json(
        { success: false, error: "Watchlist item id is required" },
        { status: 400 }
      );
    }
    const body = (await request.json()) as PatchBody;
    const { notes, targetPrice } = body;
    const item = await prisma.watchlistItem.findUnique({ where: { id } });
    if (!item) {
      return NextResponse.json(
        { success: false, error: "Watchlist item not found" },
        { status: 404 }
      );
    }
    const updated = await prisma.watchlistItem.update({
      where: { id },
      data: {
        ...(notes !== undefined && { notes: notes?.trim() || null }),
        ...(targetPrice !== undefined && {
          targetPrice:
            targetPrice != null && !Number.isNaN(Number(targetPrice)) ? Number(targetPrice) : null,
        }),
      },
      include: {
        stock: {
          select: { id: true, ticker: true, name: true, sector: true, lastPrice: true },
        },
      },
    });
    return NextResponse.json({
      success: true,
      data: { item: updated },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error updating watchlist item:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to update watchlist item",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

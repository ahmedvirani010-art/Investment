import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

type PostBody = {
  tradePlanId: string;
  entryDate: string;
  exitDate?: string | null;
  entryPrice: number;
  exitPrice?: number | null;
  quantity: number;
  realizedPL?: number | null;
  realizedPLPercent?: number | null;
  holdingPeriod?: number | null;
  strategyLabel?: string | null;
  ideaSource?: string | null;
  exitMethod?: string | null;
  entryNotes?: string | null;
  exitNotes?: string | null;
  emotionalState?: string | null;
  lessonsLearned?: string | null;
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as PostBody;
    const { tradePlanId, entryDate, entryPrice, quantity } = body;

    if (!tradePlanId || !entryDate || !entryPrice || !quantity) {
      return NextResponse.json(
        { success: false, error: "tradePlanId, entryDate, entryPrice, and quantity are required" },
        { status: 400 }
      );
    }

    const plan = await prisma.tradePlan.findUnique({
      where: { id: tradePlanId },
      include: { stock: { select: { ticker: true, name: true } } },
    });
    if (!plan) {
      return NextResponse.json({ success: false, error: "Trade plan not found" }, { status: 404 });
    }

    // Check if journal entry already exists for this plan
    const existing = await prisma.tradeJournal.findUnique({ where: { tradePlanId } });
    if (existing) {
      return NextResponse.json(
        { success: false, error: "Journal entry already exists for this plan. Use PATCH to update." },
        { status: 409 }
      );
    }

    const entry = await prisma.tradeJournal.create({
      data: {
        tradePlanId,
        entryDate: new Date(entryDate),
        exitDate: body.exitDate ? new Date(body.exitDate) : null,
        entryPrice: Number(entryPrice),
        exitPrice: body.exitPrice != null ? Number(body.exitPrice) : null,
        quantity: Number(quantity),
        realizedPL: body.realizedPL != null ? Number(body.realizedPL) : null,
        realizedPLPercent: body.realizedPLPercent != null ? Number(body.realizedPLPercent) : null,
        holdingPeriod: body.holdingPeriod != null ? Number(body.holdingPeriod) : null,
        strategyLabel: body.strategyLabel ?? null,
        ideaSource: body.ideaSource ?? null,
        exitMethod: body.exitMethod ?? null,
        entryNotes: body.entryNotes ?? null,
        exitNotes: body.exitNotes ?? null,
        emotionalState: body.emotionalState ?? null,
        lessonsLearned: body.lessonsLearned ?? null,
      },
      include: { tradePlan: { include: { stock: { select: { ticker: true, name: true } } } } },
    });

    return NextResponse.json({
      success: true,
      data: {
        entry: {
          id: entry.id,
          tradePlanId: entry.tradePlanId,
          symbol: plan.stock.ticker,
          entryDate: entry.entryDate,
          exitDate: entry.exitDate,
          entryPrice: entry.entryPrice,
          exitPrice: entry.exitPrice,
          quantity: entry.quantity,
        },
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error creating journal entry:", error);
    return NextResponse.json(
      { success: false, error: "Failed to create journal entry", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;

    // Single entry fetch by ID
    const singleId = searchParams.get("id");
    if (singleId) {
      const j = await prisma.tradeJournal.findUnique({
        where: { id: singleId },
        include: { tradePlan: { include: { stock: { select: { ticker: true, name: true } } } } },
      });
      if (!j) {
        return NextResponse.json({ success: false, error: "Journal entry not found" }, { status: 404 });
      }
      return NextResponse.json({
        success: true,
        data: {
          entry: {
            id: j.id,
            tradePlanId: j.tradePlanId,
            symbol: j.tradePlan?.stock?.ticker ?? "-",
            name: j.tradePlan?.stock?.name ?? "-",
            entryDate: j.entryDate,
            exitDate: j.exitDate,
            entryPrice: j.entryPrice,
            exitPrice: j.exitPrice,
            quantity: j.quantity,
            realizedPL: j.realizedPL,
            realizedPLPercent: j.realizedPLPercent,
            holdingPeriod: j.holdingPeriod,
            strategyLabel: j.strategyLabel,
            ideaSource: j.ideaSource,
            exitMethod: j.exitMethod,
            entryNotes: j.entryNotes,
            exitNotes: j.exitNotes,
            emotionalState: j.emotionalState,
            lessonsLearned: j.lessonsLearned,
          },
        },
        timestamp: new Date().toISOString(),
      });
    }

    const limit = Math.min(parseInt(searchParams.get("limit") ?? "50", 10), 200);

    const entries = await prisma.tradeJournal.findMany({
      include: {
        tradePlan: {
          include: {
            stock: { select: { ticker: true, name: true } },
          },
        },
      },
      orderBy: { entryDate: "desc" },
      take: limit,
    });

    const enhanced = entries.map((j) => ({
      id: j.id,
      tradePlanId: j.tradePlanId,
      symbol: j.tradePlan?.stock?.ticker ?? "-",
      name: j.tradePlan?.stock?.name ?? "-",
      entryDate: j.entryDate,
      exitDate: j.exitDate,
      entryPrice: j.entryPrice,
      exitPrice: j.exitPrice,
      quantity: j.quantity,
      realizedPL: j.realizedPL,
      realizedPLPercent: j.realizedPLPercent,
      holdingPeriod: j.holdingPeriod,
      strategyLabel: j.strategyLabel,
      ideaSource: j.ideaSource,
      exitMethod: j.exitMethod,
      entryNotes: j.entryNotes,
      exitNotes: j.exitNotes,
      emotionalState: j.emotionalState,
      lessonsLearned: j.lessonsLearned,
      createdAt: j.createdAt,
    }));

    return NextResponse.json({
      success: true,
      data: { entries: enhanced },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching trade journal:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch trade journal", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

type PatchBody = Partial<PostBody>;

export async function PATCH(request: NextRequest) {
  try {
    const body = (await request.json()) as PatchBody & { id: string };
    const { id, ...updates } = body;

    const existing = await prisma.tradeJournal.findUnique({ where: { id } });
    if (!existing) {
      return NextResponse.json({ success: false, error: "Journal entry not found" }, { status: 404 });
    }

    const data = {
      ...(updates.entryDate != null && { entryDate: new Date(updates.entryDate) }),
      ...("exitDate" in updates && { exitDate: updates.exitDate ? new Date(updates.exitDate) : null }),
      ...(updates.entryPrice != null && { entryPrice: Number(updates.entryPrice) }),
      ...("exitPrice" in updates && { exitPrice: updates.exitPrice != null ? Number(updates.exitPrice) : null }),
      ...(updates.quantity != null && { quantity: Number(updates.quantity) }),
      ...("realizedPL" in updates && { realizedPL: updates.realizedPL != null ? Number(updates.realizedPL) : null }),
      ...("realizedPLPercent" in updates && { realizedPLPercent: updates.realizedPLPercent != null ? Number(updates.realizedPLPercent) : null }),
      ...("holdingPeriod" in updates && { holdingPeriod: updates.holdingPeriod != null ? Number(updates.holdingPeriod) : null }),
      ...("strategyLabel" in updates && { strategyLabel: updates.strategyLabel ?? null }),
      ...("ideaSource" in updates && { ideaSource: updates.ideaSource ?? null }),
      ...("exitMethod" in updates && { exitMethod: updates.exitMethod ?? null }),
      ...("entryNotes" in updates && { entryNotes: updates.entryNotes ?? null }),
      ...("exitNotes" in updates && { exitNotes: updates.exitNotes ?? null }),
      ...("emotionalState" in updates && { emotionalState: updates.emotionalState ?? null }),
      ...("lessonsLearned" in updates && { lessonsLearned: updates.lessonsLearned ?? null }),
    };

    const updated = await prisma.tradeJournal.update({
      where: { id },
      data,
      include: { tradePlan: { include: { stock: { select: { ticker: true } } } } },
    });

    return NextResponse.json({
      success: true,
      data: { entry: updated },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error updating journal entry:", error);
    return NextResponse.json(
      { success: false, error: "Failed to update journal entry", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const id = searchParams.get("id");

    if (!id) {
      return NextResponse.json({ success: false, error: "id parameter is required" }, { status: 400 });
    }

    const existing = await prisma.tradeJournal.findUnique({ where: { id } });
    if (!existing) {
      return NextResponse.json({ success: false, error: "Journal entry not found" }, { status: 404 });
    }

    await prisma.tradeJournal.delete({ where: { id } });

    return NextResponse.json({
      success: true,
      data: { id },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error deleting journal entry:", error);
    return NextResponse.json(
      { success: false, error: "Failed to delete journal entry", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

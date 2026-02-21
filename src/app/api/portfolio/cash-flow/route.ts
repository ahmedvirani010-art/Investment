import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

type PostBody = { date: string; amount: number; notes?: string };

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as PostBody;
    const { date, amount } = body;

    if (!date || amount == null) {
      return NextResponse.json(
        { success: false, error: "date and amount are required" },
        { status: 400 }
      );
    }

    const amountNum = Number(amount);
    if (!Number.isFinite(amountNum)) {
      return NextResponse.json(
        { success: false, error: "amount must be a number" },
        { status: 400 }
      );
    }

    const flow = await prisma.cashFlow.create({
      data: {
        date: new Date(date),
        amount: amountNum,
        notes: body.notes ?? null,
      },
    });

    const existing = await prisma.riskSettings.findFirst({
      orderBy: { updatedAt: "desc" },
    });
    const newAccountValue = (existing?.accountValue ?? 0) + amountNum;

    if (existing) {
      await prisma.riskSettings.update({
        where: { id: existing.id },
        data: { accountValue: newAccountValue },
      });
    } else {
      await prisma.riskSettings.create({
        data: {
          accountValue: newAccountValue,
          maxRiskPerTradePct: 2,
          maxPositionSizePct: 10,
          maxTotalRiskPct: 6,
          maxSectorExposurePct: 30,
          maxSinglePositionPct: 15,
          minPositions: 5,
          maxPositions: 20,
          defaultStopLossPct: 3,
          minRewardRiskRatio: 2,
        },
      });
    }

    return NextResponse.json({
      success: true,
      data: {
        cashFlow: {
          id: flow.id,
          date: flow.date,
          amount: flow.amount,
          notes: flow.notes,
        },
        newAccountValue,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error creating cash flow:", error);
    return NextResponse.json(
      { success: false, error: "Failed to record cash flow", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const limit = Math.min(parseInt(searchParams.get("limit") ?? "100", 10), 500);
    const from = searchParams.get("from");
    const to = searchParams.get("to");

    const where: { date?: { gte?: Date; lte?: Date } } = {};
    if (from) where.date = { ...where.date, gte: new Date(from) };
    if (to) where.date = { ...where.date, lte: new Date(to) };

    const flows = await prisma.cashFlow.findMany({
      where: Object.keys(where).length ? where : undefined,
      orderBy: { date: "desc" },
      take: limit,
    });

    return NextResponse.json({
      success: true,
      data: { cashFlows: flows },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching cash flows:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch cash flows", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

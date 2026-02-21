import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

type PlanBody = {
  stockId: string;
  direction: string;
  status: string;
  entryPrice: number;
  targetPrice?: number | null;
  stopLoss: number;
  positionSize?: number | null;
  riskAmount?: number | null;
  rewardRiskRatio?: number | null;
  notes?: string | null;
  checklist?: string | null;
};

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as PlanBody;
    const { stockId, direction, status, entryPrice, targetPrice, stopLoss } = body;

    if (!stockId || !direction || !status || !entryPrice || !stopLoss) {
      return NextResponse.json(
        { success: false, error: "stockId, direction, status, entryPrice, and stopLoss are required" },
        { status: 400 }
      );
    }

    const stock = await prisma.stock.findUnique({ where: { id: stockId } });
    if (!stock) {
      return NextResponse.json({ success: false, error: "Stock not found" }, { status: 404 });
    }

    const plan = await prisma.tradePlan.create({
      data: {
        stockId,
        direction: direction.toUpperCase(),
        status: status.toUpperCase(),
        entryPrice: Number(entryPrice),
        targetPrice: targetPrice != null ? Number(targetPrice) : null,
        stopLoss: Number(stopLoss),
        positionSize: body.positionSize != null ? Number(body.positionSize) : null,
        riskAmount: body.riskAmount != null ? Number(body.riskAmount) : null,
        rewardRiskRatio: body.rewardRiskRatio != null ? Number(body.rewardRiskRatio) : null,
        notes: body.notes ?? null,
        checklist: body.checklist ?? null,
      },
      include: { stock: { select: { ticker: true, name: true, sector: true } } },
    });

    return NextResponse.json({
      success: true,
      data: {
        plan: {
          id: plan.id,
          symbol: plan.stock.ticker,
          name: plan.stock.name,
          status: plan.status,
          direction: plan.direction,
          entryPrice: plan.entryPrice,
          targetPrice: plan.targetPrice,
          stopLoss: plan.stopLoss,
          positionSize: plan.positionSize,
          riskAmount: plan.riskAmount,
          rewardRiskRatio: plan.rewardRiskRatio,
          notes: plan.notes,
        },
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error creating trade plan:", error);
    return NextResponse.json(
      { success: false, error: "Failed to create trade plan", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const status = searchParams.get("status"); // PLANNED, ACTIVE, CLOSED, CANCELLED
    const stockId = searchParams.get("stockId");
    const limit = Math.min(parseInt(searchParams.get("limit") ?? "50", 10), 200);

    const where: { status?: string; stockId?: string } = {};
    if (status) where.status = status.toUpperCase();
    if (stockId) where.stockId = stockId;

    const plans = await prisma.tradePlan.findMany({
      where,
      include: {
        stock: { select: { ticker: true, name: true, sector: true } },
      },
      orderBy: { updatedAt: "desc" },
      take: limit,
    });

    const enhanced = plans.map((p) => ({
      id: p.id,
      stockId: p.stockId,
      symbol: p.stock.ticker,
      name: p.stock.name,
      sector: p.stock.sector,
      status: p.status,
      direction: p.direction,
      entryPrice: p.entryPrice,
      targetPrice: p.targetPrice,
      stopLoss: p.stopLoss,
      positionSize: p.positionSize,
      riskAmount: p.riskAmount,
      rewardRiskRatio: p.rewardRiskRatio,
      notes: p.notes,
      checklist: p.checklist,
      createdAt: p.createdAt,
      updatedAt: p.updatedAt,
    }));

    return NextResponse.json({
      success: true,
      data: { plans: enhanced },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching trade plans:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch trade plans", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

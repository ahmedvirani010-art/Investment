import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

type PatchBody = {
  direction?: string;
  status?: string;
  entryPrice?: number;
  targetPrice?: number | null;
  stopLoss?: number;
  positionSize?: number | null;
  riskAmount?: number | null;
  rewardRiskRatio?: number | null;
  notes?: string | null;
  checklist?: string | null;
};

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = (await request.json()) as PatchBody;

    const existing = await prisma.tradePlan.findUnique({ where: { id } });
    if (!existing) {
      return NextResponse.json({ success: false, error: "Trade plan not found" }, { status: 404 });
    }

    const updated = await prisma.tradePlan.update({
      where: { id },
      data: {
        ...(body.direction != null && { direction: body.direction.toUpperCase() }),
        ...(body.status != null && { status: body.status.toUpperCase() }),
        ...(body.entryPrice != null && { entryPrice: Number(body.entryPrice) }),
        ...("targetPrice" in body && { targetPrice: body.targetPrice != null ? Number(body.targetPrice) : null }),
        ...(body.stopLoss != null && { stopLoss: Number(body.stopLoss) }),
        ...("positionSize" in body && { positionSize: body.positionSize != null ? Number(body.positionSize) : null }),
        ...("riskAmount" in body && { riskAmount: body.riskAmount != null ? Number(body.riskAmount) : null }),
        ...("rewardRiskRatio" in body && { rewardRiskRatio: body.rewardRiskRatio != null ? Number(body.rewardRiskRatio) : null }),
        ...("notes" in body && { notes: body.notes ?? null }),
        ...("checklist" in body && { checklist: body.checklist ?? null }),
      },
      include: { stock: { select: { ticker: true, name: true, sector: true } } },
    });

    return NextResponse.json({
      success: true,
      data: {
        plan: {
          id: updated.id,
          symbol: updated.stock.ticker,
          name: updated.stock.name,
          status: updated.status,
          direction: updated.direction,
          entryPrice: updated.entryPrice,
          targetPrice: updated.targetPrice,
          stopLoss: updated.stopLoss,
          positionSize: updated.positionSize,
          riskAmount: updated.riskAmount,
          rewardRiskRatio: updated.rewardRiskRatio,
          notes: updated.notes,
        },
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error updating trade plan:", error);
    return NextResponse.json(
      { success: false, error: "Failed to update trade plan", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const existing = await prisma.tradePlan.findUnique({ where: { id } });
    if (!existing) {
      return NextResponse.json({ success: false, error: "Trade plan not found" }, { status: 404 });
    }

    await prisma.tradePlan.delete({ where: { id } });

    return NextResponse.json({
      success: true,
      data: { id },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error deleting trade plan:", error);
    return NextResponse.json(
      { success: false, error: "Failed to delete trade plan", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

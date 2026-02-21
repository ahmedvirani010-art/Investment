import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET() {
  try {
    const settings = await prisma.riskSettings.findFirst({
      orderBy: { updatedAt: "desc" },
    });

    return NextResponse.json({
      success: true,
      data: { settings },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to fetch risk settings", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

type PutBody = {
  accountValue?: number;
  maxRiskPerTradePct?: number;
  maxPositionSizePct?: number;
  maxTotalRiskPct?: number;
  maxSectorExposurePct?: number;
  maxSinglePositionPct?: number;
  minPositions?: number;
  maxPositions?: number;
  defaultStopLossPct?: number;
  minRewardRiskRatio?: number;
  useKellyCriterion?: boolean;
  kellyFraction?: number;
  allowPyramiding?: boolean;
  maxCorrelatedPositions?: number;
};

export async function PUT(request: NextRequest) {
  try {
    const body = (await request.json()) as PutBody;

    const existing = await prisma.riskSettings.findFirst({
      orderBy: { updatedAt: "desc" },
    });

    const data = {
      ...(body.accountValue != null && { accountValue: Number(body.accountValue) }),
      ...(body.maxRiskPerTradePct != null && { maxRiskPerTradePct: Number(body.maxRiskPerTradePct) }),
      ...(body.maxPositionSizePct != null && { maxPositionSizePct: Number(body.maxPositionSizePct) }),
      ...(body.maxTotalRiskPct != null && { maxTotalRiskPct: Number(body.maxTotalRiskPct) }),
      ...(body.maxSectorExposurePct != null && { maxSectorExposurePct: Number(body.maxSectorExposurePct) }),
      ...(body.maxSinglePositionPct != null && { maxSinglePositionPct: Number(body.maxSinglePositionPct) }),
      ...(body.minPositions != null && { minPositions: Number(body.minPositions) }),
      ...(body.maxPositions != null && { maxPositions: Number(body.maxPositions) }),
      ...(body.defaultStopLossPct != null && { defaultStopLossPct: Number(body.defaultStopLossPct) }),
      ...(body.minRewardRiskRatio != null && { minRewardRiskRatio: Number(body.minRewardRiskRatio) }),
      ...(body.useKellyCriterion != null && { useKellyCriterion: Boolean(body.useKellyCriterion) }),
      ...(body.kellyFraction != null && { kellyFraction: Number(body.kellyFraction) }),
      ...(body.allowPyramiding != null && { allowPyramiding: Boolean(body.allowPyramiding) }),
      ...(body.maxCorrelatedPositions != null && { maxCorrelatedPositions: Number(body.maxCorrelatedPositions) }),
    };

    let settings;
    if (existing) {
      settings = await prisma.riskSettings.update({
        where: { id: existing.id },
        data,
      });
    } else {
      settings = await prisma.riskSettings.create({
        data: {
          accountValue: body.accountValue ?? 0,
          ...data,
        },
      });
    }

    return NextResponse.json({
      success: true,
      data: { settings },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to update risk settings", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

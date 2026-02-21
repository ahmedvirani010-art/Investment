import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/**
 * Risk metrics from existing Prisma data (RiskSettings + holdings).
 * Computes portfolio-level risk view without calling Python.
 */
export async function GET(request: NextRequest) {
  try {
    const [settingsList, holdings] = await Promise.all([
      prisma.riskSettings.findFirst({ orderBy: { updatedAt: "desc" } }),
      prisma.userStock.findMany({
        where: { totalQuantity: { gt: 0 } },
        include: {
          stock: { select: { ticker: true, name: true, sector: true, lastPrice: true } },
        },
        orderBy: { totalInvested: "desc" },
      }),
    ]);

    const settings = settingsList ?? {
      accountValue: 0,
      maxRiskPerTradePct: 2,
      maxPositionSizePct: 10,
      maxTotalRiskPct: 6,
      maxSectorExposurePct: 30,
      maxSinglePositionPct: 15,
      minPositions: 5,
      maxPositions: 20,
      defaultStopLossPct: 3,
      minRewardRiskRatio: 2,
      useKellyCriterion: false,
      kellyFraction: 0.25,
      allowPyramiding: true,
      maxCorrelatedPositions: 3,
    };

    const accountValue = settings.accountValue;
    const totalEquity = holdings.reduce((sum, h) => {
      const price = h.stock.lastPrice ?? h.averageCost ?? 0;
      return sum + h.totalQuantity * price;
    }, 0);
    const effectiveAccountValue = accountValue > 0 ? accountValue : totalEquity;

    const sectorExposure: Record<string, { value: number; pct: number }> = {};
    let totalRiskPct = 0;
    const violations: { type: string; message: string; value?: number }[] = [];

    for (const h of holdings) {
      const price = h.stock.lastPrice ?? h.averageCost ?? 0;
      const value = h.totalQuantity * price;
      const sector = h.stock.sector ?? "Unknown";
      sectorExposure[sector] = sectorExposure[sector] ?? { value: 0, pct: 0 };
      sectorExposure[sector].value += value;
    }

    if (effectiveAccountValue > 0) {
      for (const s of Object.keys(sectorExposure)) {
        sectorExposure[s].pct = (sectorExposure[s].value / effectiveAccountValue) * 100;
        if (sectorExposure[s].pct > settings.maxSectorExposurePct) {
          violations.push({
            type: "sector_concentration",
            message: `Sector ${s} exceeds ${settings.maxSectorExposurePct}%`,
            value: sectorExposure[s].pct,
          });
        }
      }

      for (const h of holdings) {
        const price = h.stock.lastPrice ?? h.averageCost ?? 0;
        const value = h.totalQuantity * price;
        const positionPct = (value / effectiveAccountValue) * 100;
        if (positionPct > settings.maxSinglePositionPct) {
          violations.push({
            type: "position_size",
            message: `${h.stock.ticker} position ${positionPct.toFixed(1)}% exceeds max ${settings.maxSinglePositionPct}%`,
            value: positionPct,
          });
        }
      }

      if (holdings.length < settings.minPositions && settings.minPositions > 0) {
        violations.push({
          type: "diversification",
          message: `Positions (${holdings.length}) below minimum (${settings.minPositions})`,
        });
      }
      if (holdings.length > settings.maxPositions) {
        violations.push({
          type: "diversification",
          message: `Positions (${holdings.length}) above maximum (${settings.maxPositions})`,
        });
      }
    }

    const diversificationScore =
      effectiveAccountValue > 0 && settings.maxPositions > 0
        ? Math.min(100, (holdings.length / settings.maxPositions) * 100)
        : 0;

    const summary = {
      accountValue: effectiveAccountValue,
      totalEquity,
      totalRiskPct,
      diversificationScore: Math.round(diversificationScore),
      sectorExposure: Object.entries(sectorExposure).map(([name, data]) => ({
        sector: name,
        value: data.value,
        pct: Math.round(data.pct * 10) / 10,
      })),
      violations,
      settings: {
        maxRiskPerTradePct: settings.maxRiskPerTradePct,
        maxPositionSizePct: settings.maxPositionSizePct,
        maxTotalRiskPct: settings.maxTotalRiskPct,
        maxSectorExposurePct: settings.maxSectorExposurePct,
        maxSinglePositionPct: settings.maxSinglePositionPct,
        minPositions: settings.minPositions,
        maxPositions: settings.maxPositions,
        defaultStopLossPct: settings.defaultStopLossPct,
        minRewardRiskRatio: settings.minRewardRiskRatio,
      },
    };

    return NextResponse.json({
      success: true,
      data: { summary, positionsCount: holdings.length },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching risk metrics:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch risk metrics",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

/**
 * Money-Weighted Return (Modified Dietz) over a period.
 * GET /api/portfolio/returns?period=30d|90d|1y
 * Uses AccountSnapshot for BMV/EMV when available; falls back to current holdings for EMV.
 */
function getPeriodDays(period: string): number | null {
  const m = period.match(/^(\d+)(d|w|y)$/i);
  if (!m) return null;
  const n = parseInt(m[1], 10);
  if (m[2].toLowerCase() === "d") return n;
  if (m[2].toLowerCase() === "w") return n * 7;
  if (m[2].toLowerCase() === "y") return n * 365;
  return null;
}

/**
 * Modified Dietz: MWR = (EMV - BMV - NCF) / (BMV + sum(CF_i * w_i))
 * where w_i = (days from flow to end) / totalDays (weight = fraction of period flow was invested)
 */
function modifiedDietz(
  bmv: number,
  emv: number,
  cashFlows: { date: Date; amount: number }[],
  startDate: Date,
  endDate: Date
): number | null {
  const totalMs = endDate.getTime() - startDate.getTime();
  const totalDays = totalMs / (1000 * 60 * 60 * 24);
  if (totalDays <= 0 || bmv <= 0) return null;

  const ncf = cashFlows.reduce((s, f) => s + f.amount, 0);
  let weightedSum = 0;
  for (const f of cashFlows) {
    const daysToEnd = (endDate.getTime() - f.date.getTime()) / (1000 * 60 * 60 * 24);
    const w = Math.max(0, Math.min(1, daysToEnd / totalDays));
    weightedSum += f.amount * w;
  }

  const denominator = bmv + weightedSum;
  if (denominator <= 0) return null;
  const mwr = (emv - bmv - ncf) / denominator;
  return mwr * 100; // as percentage
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const period = searchParams.get("period") ?? "30d";
    const days = getPeriodDays(period);
    if (days == null || days <= 0) {
      return NextResponse.json(
        { success: false, error: "Invalid period. Use e.g. 30d, 90d, 1y" },
        { status: 400 }
      );
    }

    const endDate = new Date();
    endDate.setHours(23, 59, 59, 999);
    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - days);
    startDate.setHours(0, 0, 0, 0);

    const [snapshots, cashFlows, holdingsSummary, riskSettings] = await Promise.all([
      prisma.accountSnapshot.findMany({
        where: { date: { gte: startDate, lte: endDate } },
        orderBy: { date: "asc" },
      }),
      prisma.cashFlow.findMany({
        where: { date: { gt: startDate, lte: endDate } },
        orderBy: { date: "asc" },
      }),
      prisma.userStock.findMany({
        where: { totalQuantity: { gt: 0 } },
        include: { stock: { select: { lastPrice: true } } },
      }),
      prisma.riskSettings.findFirst(),
    ]);

    const currentEquityValue = holdingsSummary.reduce((sum, h) => {
      const price = h.stock?.lastPrice ?? h.averageCost ?? 0;
      return sum + h.totalQuantity * price;
    }, 0);
    const currentPortfolioValue =
      riskSettings?.accountValue != null && riskSettings.accountValue > 0
        ? riskSettings.accountValue
        : currentEquityValue;

    const flowsForDietz = cashFlows.map((f) => ({ date: f.date, amount: f.amount }));

    let bmv: number;
    let emv: number;
    const snapshotAtStart = snapshots.filter((s) => s.date <= startDate).pop();
    const snapshotAtEnd = snapshots.filter((s) => s.date <= endDate).pop();

    if (snapshotAtStart) {
      bmv = snapshotAtStart.totalValue;
    } else {
      if (snapshotAtEnd) {
        bmv = snapshotAtEnd.totalValue - flowsForDietz.reduce((s, f) => s + f.amount, 0);
      } else {
        bmv = currentPortfolioValue - flowsForDietz.reduce((s, f) => s + f.amount, 0);
      }
      bmv = Math.max(0, bmv);
    }

    if (snapshotAtEnd) {
      emv = snapshotAtEnd.totalValue;
    } else {
      emv = currentPortfolioValue;
    }

    const mwr = modifiedDietz(bmv, emv, flowsForDietz, startDate, endDate);

    const periodLabel =
      days <= 31 ? `${days}d` : days <= 365 ? `${Math.round(days / 30)}m` : `${(days / 365).toFixed(1)}y`;

    return NextResponse.json({
      success: true,
      data: {
        period,
        periodDays: days,
        periodLabel,
        startDate: startDate.toISOString(),
        endDate: endDate.toISOString(),
        bmv,
        emv,
        netCashFlow: flowsForDietz.reduce((s, f) => s + f.amount, 0),
        moneyWeightedReturnPct: mwr,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error computing returns:", error);
    return NextResponse.json(
      { success: false, error: "Failed to compute returns", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

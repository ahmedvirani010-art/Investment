import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
  try {
    // Get current portfolio holdings with stock details and current prices
    const holdings = await prisma.userStock.findMany({
      where: {
        totalQuantity: {
          gt: 0, // Only show stocks with actual holdings
        },
      },
      include: {
        stock: {
          select: {
            ticker: true,
            name: true,
            sector: true,
            lastPrice: true,
          },
        },
      },
      orderBy: {
        totalInvested: "desc",
      },
    });

    // Calculate derived metrics for each holding
    const holdingsWithMetrics = holdings.map((holding) => {
      const currentPrice = holding.stock.lastPrice || 0;
      const averageCost = holding.averageCost;
      const quantity = holding.totalQuantity;
      const currentValue = currentPrice * quantity;
      const unrealizedPL = currentValue - holding.totalInvested;
      const unrealizedPLPercent = holding.totalInvested > 0 
        ? (unrealizedPL / holding.totalInvested) * 100 
        : 0;

      return {
        id: holding.id,
        stockId: holding.stockId,
        symbol: holding.stock.ticker,
        name: holding.stock.name,
        sector: holding.stock.sector,
        quantity: quantity,
        averageCost: averageCost,
        currentPrice: currentPrice,
        totalCost: holding.totalInvested,
        currentValue: currentValue,
        unrealizedPL: unrealizedPL,
        unrealizedPLPercent: unrealizedPLPercent,
        realizedGain: holding.realizedGain,
        totalDividends: holding.totalDividends,
      };
    });

    // Calculate portfolio summary
    const totalValue = holdingsWithMetrics.reduce((sum, h) => sum + h.currentValue, 0);
    const totalCost = holdingsWithMetrics.reduce((sum, h) => sum + h.totalCost, 0);
    const totalUnrealizedPL = totalValue - totalCost;
    const totalRealizedGain = holdingsWithMetrics.reduce((sum, h) => sum + h.realizedGain, 0);
    const totalDividends = holdingsWithMetrics.reduce((sum, h) => sum + h.totalDividends, 0);

    const summary = {
      totalValue,
      totalCost,
      totalUnrealizedPL,
      totalUnrealizedPLPercent: totalCost > 0 ? (totalUnrealizedPL / totalCost) * 100 : 0,
      totalRealizedGain,
      totalDividends,
      totalReturnUnrealized: totalUnrealizedPL + totalRealizedGain + totalDividends,
      totalReturnPercent: totalCost > 0 ? ((totalUnrealizedPL + totalRealizedGain + totalDividends) / totalCost) * 100 : 0,
      numberOfPositions: holdingsWithMetrics.length,
    };

    return NextResponse.json({
      success: true,
      data: {
        holdings: holdingsWithMetrics,
        summary,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Error fetching portfolio holdings:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch portfolio holdings",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}
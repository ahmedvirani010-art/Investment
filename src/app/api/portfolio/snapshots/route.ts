import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const limit = searchParams.get("limit") || "30";
    const limitNum = parseInt(limit, 10);

    // Get portfolio snapshots for the last N days
    const snapshots = await prisma.accountSnapshot.findMany({
      orderBy: {
        date: "desc",
      },
      take: limitNum,
    });

    // Calculate additional metrics for each snapshot
    const enhancedSnapshots = snapshots.map((snapshot) => {
      const timeWeightedReturn = snapshot.investedValue > 0 
        ? (snapshot.unrealizedPL / snapshot.investedValue) * 100 
        : 0;
      
      return {
        ...snapshot,
        timeWeightedReturn,
        totalReturn: snapshot.unrealizedPL + snapshot.realizedPL,
        totalReturnPercent: snapshot.totalValue > 0 
          ? ((snapshot.unrealizedPL + snapshot.realizedPL) / (snapshot.totalValue - snapshot.unrealizedPL - snapshot.realizedPL)) * 100 
          : 0,
      };
    });

    // Calculate summary statistics
    if (enhancedSnapshots.length === 0) {
      return NextResponse.json({
        success: true,
        data: {
          snapshots: [],
          summary: null,
        },
        timestamp: new Date().toISOString(),
      });
    }

    const latestSnapshot = enhancedSnapshots[0];
    const oldestSnapshot = enhancedSnapshots[enhancedSnapshots.length - 1];
    
    const periodReturn = oldestSnapshot.totalValue > 0 
      ? ((latestSnapshot.totalValue - oldestSnapshot.totalValue) / oldestSnapshot.totalValue) * 100 
      : 0;

    const summary = {
      currentValue: latestSnapshot.totalValue,
      currentUnrealizedPL: latestSnapshot.unrealizedPL,
      currentRealizedPL: latestSnapshot.realizedPL,
      periodReturn,
      periodVolatility: enhancedSnapshots.length > 1
        ? calculateVolatility(enhancedSnapshots.map(s => s.totalReturnPercent))
        : 0,
      maxValue: Math.max(...enhancedSnapshots.map(s => s.totalValue)),
      minValue: Math.min(...enhancedSnapshots.map(s => s.totalValue)),
      averageValue: enhancedSnapshots.reduce((sum, s) => sum + s.totalValue, 0) / enhancedSnapshots.length,
    };

    return NextResponse.json({
      success: true,
      data: {
        snapshots: enhancedSnapshots,
        summary,
      },
      timestamp: new Date().toISOString(),
    });

  } catch (error) {
    console.error("Error fetching portfolio snapshots:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch portfolio snapshots",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

function calculateVolatility(returns: number[]): number {
  if (returns.length <= 1) return 0;
  
  const mean = returns.reduce((sum, r) => sum + r, 0) / returns.length;
  const variance = returns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / (returns.length - 1);
  return Math.sqrt(variance);
}
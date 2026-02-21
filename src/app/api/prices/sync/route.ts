import { NextResponse } from "next/server";
import { syncPrices } from "@/lib/sync-prices";

export const maxDuration = 120;

export async function POST() {
  try {
    const result = await syncPrices();
    return NextResponse.json({
      success: true,
      data: {
        updated: result.updated,
        errors: result.errors,
        total: result.total,
      },
      timestamp: new Date().toISOString(),
    });
  } catch (e) {
    const details = e instanceof Error ? e.message : "Unknown error";
    console.error("Error syncing prices:", details, e);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to sync prices",
        details,
      },
      { status: 500 }
    );
  }
}

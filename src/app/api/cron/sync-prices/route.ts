import { NextRequest, NextResponse } from "next/server";
import { syncPrices } from "@/lib/sync-prices";

export const maxDuration = 120;

export async function GET(request: NextRequest) {
  const secret = process.env.CRON_SECRET;
  if (secret) {
    const auth =
      request.headers.get("authorization")?.replace(/^Bearer\s+/i, "") ??
      request.nextUrl.searchParams.get("secret");
    if (auth !== secret) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
  }

  try {
    const result = await syncPrices();
    return NextResponse.json({
      success: true,
      data: result,
      timestamp: new Date().toISOString(),
    });
  } catch (e) {
    console.error("Cron sync-prices error:", e);
    return NextResponse.json(
      {
        success: false,
        error: e instanceof Error ? e.message : "Sync failed",
      },
      { status: 500 }
    );
  }
}

import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";
import { prisma } from "@/lib/prisma";

export const maxDuration = 60;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const lookbackDays = searchParams.get("lookback_days") ?? "30";
  const minPrice = searchParams.get("min_price") ?? "20";
  const topN = searchParams.get("top_n") ?? "50";

  const pythonCmd = process.env.PYTHON_PATH ?? (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(process.cwd(), "scripts", "api_liquidity.py");

  let stocksPayload = "";
  try {
    const stocks = await prisma.stock.findMany({
      where: { isActive: true },
      select: { ticker: true, name: true },
      orderBy: { ticker: "asc" },
    });
    stocksPayload = JSON.stringify(stocks.map((s) => ({ ticker: s.ticker, name: s.name })));
  } catch (e) {
    console.error("Liquidity: failed to load stocks from DB", e);
    return NextResponse.json(
      { success: false, error: "Failed to load stock list", details: String(e) },
      { status: 500 }
    );
  }

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(pythonCmd, [scriptPath, lookbackDays, minPrice, topN], {
      cwd: process.cwd(),
      timeout: 120000,
      stdio: ["pipe", "pipe", "pipe"],
    });

    let stdout = "";
    let stderr = "";

    proc.stdout?.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    proc.stderr?.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    if (stocksPayload && proc.stdin) {
      proc.stdin.write(stocksPayload, "utf8", () => {
        proc.stdin?.end();
      });
    }

    proc.on("close", (code) => {
      if (code !== 0) {
        console.error("Liquidity script stderr:", stderr);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Liquidity analysis failed",
              details: stderr || `Exit code ${code}`,
            },
            { status: 500 }
          )
        );
        return;
      }

      try {
        const result = JSON.parse(stdout.trim());
        if (result.success) {
          resolve(NextResponse.json(result));
        } else {
          resolve(
            NextResponse.json(
              { success: false, error: result.error ?? "Unknown error" },
              { status: 500 }
            )
          );
        }
      } catch (e) {
        console.error("Liquidity parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from liquidity script",
              details: e instanceof Error ? e.message : "Parse error",
            },
            { status: 500 }
          )
        );
      }
    });

    proc.on("error", (err) => {
      resolve(
        NextResponse.json(
          {
            success: false,
            error: "Failed to run liquidity analysis",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

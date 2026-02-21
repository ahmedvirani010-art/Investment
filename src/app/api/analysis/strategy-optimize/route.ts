import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 120;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const symbol = searchParams.get("symbol") ?? "BTC-USD";
  const period = searchParams.get("period") ?? "730d";
  const interval = searchParams.get("interval") ?? "1h";
  const nTrials = searchParams.get("n_trials") ?? "20";
  const metric = searchParams.get("metric") ?? "total_return";

  const pythonCmd =
    process.env.PYTHON_PATH ??
    (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(
    process.cwd(),
    "scripts",
    "optimize_hmm_backtest.py"
  );

  const args = [
    scriptPath,
    symbol.trim(),
    "--period",
    period,
    "--interval",
    interval,
    "--n-trials",
    nTrials,
    "--metric",
    metric,
  ];

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(pythonCmd, args, {
      cwd: process.cwd(),
      timeout: 300000,
    });

    let stdout = "";
    let stderr = "";

    proc.stdout?.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    proc.stderr?.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        console.error("Strategy optimize stderr:", stderr);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Strategy optimization failed",
              details: stderr || `Exit code ${code}`,
            },
            { status: 500 }
          )
        );
        return;
      }

      try {
        const data = JSON.parse(stdout.trim());
        resolve(NextResponse.json({ success: true, data }));
      } catch (e) {
        console.error("Strategy optimize parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from strategy optimization",
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
            error: "Failed to run strategy optimization",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

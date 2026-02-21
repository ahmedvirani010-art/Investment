import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 90;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const symbol = searchParams.get("symbol") ?? "BTC-USD";
  const period = searchParams.get("period") ?? "365d";
  const interval = searchParams.get("interval") ?? "1h";
  const nFolds = searchParams.get("n_folds") ?? "4";
  const nComponents = searchParams.get("n_components") ?? "7";

  const pythonCmd =
    process.env.PYTHON_PATH ??
    (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(
    process.cwd(),
    "scripts",
    "api_walk_forward.py"
  );

  const args = [
    scriptPath,
    symbol.trim(),
    "--period",
    period,
    "--interval",
    interval,
    "--n-folds",
    nFolds,
    "--n-components",
    nComponents,
  ];

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(pythonCmd, args, {
      cwd: process.cwd(),
      timeout: 120000,
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
        console.error("Walk-forward stderr:", stderr);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Walk-forward validation failed",
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
        console.error("Walk-forward parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from walk-forward",
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
            error: "Failed to run walk-forward validation",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

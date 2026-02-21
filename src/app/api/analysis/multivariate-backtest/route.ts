import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 90;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const assets = searchParams.get("assets") ?? undefined;
  const period = searchParams.get("period") ?? "730d";
  const nComponents = searchParams.get("n_components") ?? "7";

  const pythonCmd =
    process.env.PYTHON_PATH ??
    (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(
    process.cwd(),
    "scripts",
    "api_multivariate_backtest.py"
  );

  const args = [
    scriptPath,
    "--period",
    period,
    "--n-components",
    nComponents,
  ];
  if (assets?.trim()) {
    args.push("--assets", assets.trim());
  }

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
        console.error("Multivariate backtest stderr:", stderr);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Multivariate backtest failed",
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
        console.error(
          "Multivariate backtest parse error:",
          stdout?.slice(0, 200)
        );
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from multivariate backtest",
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
            error: "Failed to run multivariate backtest",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

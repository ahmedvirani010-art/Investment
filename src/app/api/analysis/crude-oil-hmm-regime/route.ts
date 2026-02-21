import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 90;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const symbol = searchParams.get("symbol") ?? "CL=F";
  const period = searchParams.get("period") ?? "730d";
  const interval = searchParams.get("interval") ?? "1d";
  const nComponents = searchParams.get("n_components") ?? "7";
  const lastN = searchParams.get("last_n") ?? "500";

  const pythonCmd =
    process.env.PYTHON_PATH ??
    (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(
    process.cwd(),
    "scripts",
    "api_crude_oil_hmm_regime.py"
  );

  const args = [
    scriptPath,
    symbol.trim(),
    "--period",
    period,
    "--interval",
    interval,
    "--n-components",
    nComponents,
    "--last-n",
    lastN,
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
        console.error("Crude oil HMM regime script stderr:", stderr);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Crude oil HMM regime analysis failed",
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
        console.error("Crude oil HMM regime parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from crude oil HMM regime script",
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
            error: "Failed to run crude oil HMM regime analysis",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 90;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const lookbackDays = searchParams.get("lookback_days") ?? "60";
  const zThreshold = searchParams.get("z_threshold") ?? "2.5";
  const symbols = searchParams.get("symbols") ?? "";

  const pythonCmd = process.env.PYTHON_PATH ?? (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(process.cwd(), "scripts", "api_anomalies.py");

  const args = [scriptPath, lookbackDays, zThreshold];
  if (symbols.trim()) args.push(symbols.trim());

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
        console.error("Anomalies script stderr:", stderr);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Anomaly detection failed",
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
        console.error("Anomalies parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from anomaly script",
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
            error: "Failed to run anomaly detection",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 90;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const symbol = searchParams.get("symbol") ?? "BTC-USD";
  const period = searchParams.get("period") ?? "730d";
  const interval = searchParams.get("interval") ?? "1h";
  const nComponents = searchParams.get("n_components") ?? "7";
  const cooldownHours = searchParams.get("cooldown_hours");
  const leverage = searchParams.get("leverage");
  const minConfirmations = searchParams.get("min_confirmations");
  const allowShort = searchParams.get("allow_short");
  const minBearConfirmations = searchParams.get("min_bear_confirmations");
  const useAgentVeto = searchParams.get("use_agent_veto");

  const pythonCmd =
    process.env.PYTHON_PATH ??
    (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(
    process.cwd(),
    "scripts",
    "api_hmm_regime_backtest.py"
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
  ];
  if (cooldownHours != null && cooldownHours !== "") args.push("--cooldown-hours", cooldownHours);
  if (leverage != null && leverage !== "") args.push("--leverage", leverage);
  if (minConfirmations != null && minConfirmations !== "") args.push("--min-confirmations", minConfirmations);
  if (allowShort === "true" || allowShort === "1") args.push("--allow-short");
  if (minBearConfirmations != null && minBearConfirmations !== "") args.push("--min-bear-confirmations", minBearConfirmations);
  if (useAgentVeto === "true" || useAgentVeto === "1") args.push("--use-agent-veto");

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
        console.error("HMM regime backtest stderr:", stderr);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "HMM regime backtest failed",
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
        console.error("HMM regime backtest parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from HMM regime backtest",
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
            error: "Failed to run HMM regime backtest",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

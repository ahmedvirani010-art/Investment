import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 90;

const DEFAULT_SYMBOLS = "LUCK,PSO,HBL,ENGRO,MCB,OGDC,PPL,UBL,HUBC,FFC";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const mode = searchParams.get("mode") ?? "quick";
  const symbol = searchParams.get("symbol") ?? "";
  const symbols = searchParams.get("symbols") ?? "";

  if (mode !== "quick" && mode !== "deep" && mode !== "screen") {
    return NextResponse.json(
      { success: false, error: "Invalid mode. Use quick, deep, or screen." },
      { status: 400 }
    );
  }

  if ((mode === "quick" || mode === "deep") && !symbol.trim()) {
    return NextResponse.json(
      { success: false, error: "Symbol required for quick and deep mode." },
      { status: 400 }
    );
  }

  const pythonCmd =
    process.env.PYTHON_PATH ??
    (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(process.cwd(), "scripts", "api_fundamental.py");

  const args = [scriptPath, mode];
  if (mode === "screen") {
    args.push(symbols.trim() || DEFAULT_SYMBOLS);
  } else {
    args.push(symbol.trim().toUpperCase().replace(".KA", ""));
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
        console.error("Fundamental script stderr:", stderr);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Fundamental analysis failed",
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
        console.error("Fundamental parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from fundamental script",
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
            error: "Failed to run fundamental analysis",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

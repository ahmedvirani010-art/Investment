import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 90;

const DEFAULT_SYMBOLS = "LUCK,PSO,HBL,ENGRO,MCB,OGDC,PPL,UBL,HUBC,FFC";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const mode = searchParams.get("mode") ?? "single";
  const symbol = searchParams.get("symbol") ?? "";
  const symbols = searchParams.get("symbols") ?? "";
  const filterParam = searchParams.get("filter") ?? "both";

  if (mode !== "single" && mode !== "batch" && mode !== "mtf" && mode !== "screen") {
    return NextResponse.json(
      { success: false, error: "Invalid mode. Use single, batch, mtf, or screen." },
      { status: 400 }
    );
  }

  if ((mode === "single" || mode === "mtf") && !symbol.trim()) {
    return NextResponse.json(
      { success: false, error: "Symbol required for single and mtf mode." },
      { status: 400 }
    );
  }

  const pythonCmd =
    process.env.PYTHON_PATH ??
    (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(process.cwd(), "scripts", "api_technical.py");

  const args = [scriptPath, mode];
  if (mode === "single" || mode === "mtf") {
    args.push(symbol.trim().toUpperCase().replace(".KA", ""));
  } else if (mode === "batch") {
    args.push(symbols.trim() || DEFAULT_SYMBOLS);
  } else {
    args.push(symbols.trim() || DEFAULT_SYMBOLS);
    const filter = ["overbought", "oversold", "both"].includes(filterParam.toLowerCase())
      ? filterParam.toLowerCase()
      : "both";
    args.push(filter);
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
        console.error("Technical script stderr:", stderr);
        const details = stderr || `Exit code ${code}`;
        const isRefused = /connection refused|ECONNREFUSED|refused/i.test(details);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Technical analysis failed",
              details,
              ...(isRefused && {
                hint: "Connection refused often means the dev server is not running, or outbound access (e.g. to OpenRouter for AI summary) is blocked. See README Troubleshooting.",
              }),
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
        console.error("Technical parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from technical script",
              details: e instanceof Error ? e.message : "Parse error",
            },
            { status: 500 }
          )
        );
      }
    });

    proc.on("error", (err: NodeJS.ErrnoException) => {
      const msg = err.message || "";
      const isRefused = msg.includes("ECONNREFUSED") || /refused/i.test(msg);
      resolve(
        NextResponse.json(
          {
            success: false,
            error: "Failed to run technical analysis",
            details: msg,
            ...(isRefused && {
              hint: "Connection refused: ensure the dev server is running (npm run dev) and you are using the correct URL (e.g. http://localhost:3000). See README Troubleshooting.",
            }),
          },
          { status: 500 }
        )
      );
    });
  });
}

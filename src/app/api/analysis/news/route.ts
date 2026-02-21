import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 120;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const mode = searchParams.get("mode") ?? "";
  const hoursParam = searchParams.get("hours");
  const limitParam = searchParams.get("limit");
  const symbolsParam = searchParams.get("symbols") ?? "";
  const daysParam = searchParams.get("days");

  const validModes = ["fetch", "recent", "symbols", "macro"];
  if (!validModes.includes(mode)) {
    return NextResponse.json(
      {
        success: false,
        error: `Invalid or missing mode. Use one of: ${validModes.join(", ")}`,
      },
      { status: 400 }
    );
  }

  const pythonCmd =
    process.env.PYTHON_PATH ?? (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(process.cwd(), "scripts", "api_news.py");

  const args: string[] = [scriptPath, mode];

  if (mode === "fetch") {
    const hours = hoursParam ? String(parseInt(hoursParam, 10) || 48) : "48";
    args.push(hours);
  } else if (mode === "recent") {
    const hours = hoursParam ? String(parseInt(hoursParam, 10) || 24) : "24";
    const limit = limitParam ? String(parseInt(limitParam, 10) || 50) : "50";
    args.push(hours, limit);
  } else if (mode === "symbols") {
    if (!symbolsParam.trim()) {
      return NextResponse.json(
        { success: false, error: "symbols param required for symbols mode" },
        { status: 400 }
      );
    }
    const days = daysParam ? String(parseInt(daysParam, 10) || 7) : "7";
    args.push(symbolsParam.trim(), days);
  } else {
    // macro
    const hours = hoursParam ? String(parseInt(hoursParam, 10) || 48) : "48";
    args.push(hours);
  }

  const timeoutMs = mode === "fetch" ? 180000 : 60000;

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(pythonCmd, args, {
      cwd: process.cwd(),
      timeout: timeoutMs,
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
        console.error("News script stderr:", stderr);
        const isMissingModule =
          /ModuleNotFoundError|No module named/i.test(stderr);
        const hint = isMissingModule
          ? " Install Python dependencies from the project root: py -m pip install -r requirements.txt (Windows) or pip install -r requirements.txt (Linux/Mac)."
          : "";
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "News agent failed" + hint,
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
        console.error("News parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from news script",
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
            error: "Failed to run news agent",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

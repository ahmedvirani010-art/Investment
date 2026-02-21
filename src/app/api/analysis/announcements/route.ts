import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export const maxDuration = 120;

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const action = searchParams.get("action") ?? "list";
  const days = searchParams.get("days") ?? "7";
  const symbols = searchParams.get("symbols") ?? "";
  const tier = searchParams.get("tier") ?? "";

  const pythonCmd =
    process.env.PYTHON_PATH ?? (process.platform === "win32" ? "py" : "python3");
  const scriptPath = path.join(process.cwd(), "scripts", "api_announcements.py");

  const args = [scriptPath, action, days];
  if (action === "list") {
    const tierVal = tier.trim();
    const hasTier = ["1", "2", "3"].includes(tierVal);
    const symbolsVal = symbols.trim();
    if (hasTier) {
      args.push(symbolsVal || "ALL");
      args.push(tierVal);
    } else if (symbolsVal) {
      args.push(symbolsVal);
    }
  }

  const timeout = action === "sync" ? 120000 : 60000;

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(pythonCmd, args, {
      cwd: process.cwd(),
      timeout,
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
        console.error("Announcements script stderr:", stderr);
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Announcements request failed",
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
        console.error("Announcements parse error:", stdout?.slice(0, 200));
        resolve(
          NextResponse.json(
            {
              success: false,
              error: "Invalid response from announcements script",
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
            error: "Failed to run announcements script",
            details: err.message,
          },
          { status: 500 }
        )
      );
    });
  });
}

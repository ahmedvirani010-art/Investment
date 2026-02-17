import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { buildOpenRouterHeaders, OPENROUTER_BASE_URL } from "@/lib/openrouter";

const MessageSchema = z.object({
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
});

const ChatSchema = z.object({
  messages: z.array(MessageSchema).min(1),
  model: z.string().optional(),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = ChatSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0].message },
        { status: 400 }
      );
    }

    const settings = await prisma.llmSettings.findFirst();
    if (!settings?.apiKey) {
      return NextResponse.json(
        { error: "API key not configured. Go to Settings and enter your OpenRouter API key." },
        { status: 400 }
      );
    }

    const model = parsed.data.model ?? settings.model;
    const { messages } = parsed.data;

    const response = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
      method: "POST",
      headers: buildOpenRouterHeaders(settings.apiKey),
      body: JSON.stringify({ model, messages, stream: true }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `OpenRouter error: ${errorText}` },
        { status: response.status }
      );
    }

    // Proxy the SSE stream directly to the client
    return new NextResponse(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
    });
  } catch {
    return NextResponse.json({ error: "Failed to process chat request" }, { status: 500 });
  }
}

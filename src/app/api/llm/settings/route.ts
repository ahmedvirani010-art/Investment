import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { prisma } from "@/lib/prisma";
import { DEFAULT_MODEL_ID, isValidModelId } from "@/lib/openrouter-models";

export async function GET() {
  try {
    const settings = await prisma.llmSettings.findFirst();
    return NextResponse.json({
      model: settings?.model ?? DEFAULT_MODEL_ID,
      hasApiKey: !!settings?.apiKey,
    });
  } catch {
    return NextResponse.json({ error: "Failed to load settings" }, { status: 500 });
  }
}

const SettingsSchema = z.object({
  apiKey: z.string().min(1, "API key is required"),
  model: z.string().refine(isValidModelId, "Invalid model ID"),
});

export async function PUT(request: NextRequest) {
  try {
    const body = await request.json();
    const parsed = SettingsSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0].message },
        { status: 400 }
      );
    }

    const { apiKey, model } = parsed.data;
    const settings = await prisma.llmSettings.upsert({
      where: { id: "singleton" },
      update: { apiKey, model },
      create: { id: "singleton", apiKey, model },
    });

    return NextResponse.json({ success: true, model: settings.model });
  } catch {
    return NextResponse.json({ error: "Failed to save settings" }, { status: 500 });
  }
}

import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { PSX_SECTORS } from "@/lib/psx-data";

export async function GET() {
  try {
    const sectors = await prisma.sector.findMany({
      orderBy: [{ displayOrder: "asc" }, { name: "asc" }],
    });
    return NextResponse.json({
      success: true,
      data: { sectors },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching sectors:", error);
    return NextResponse.json(
      { success: false, error: "Failed to fetch sectors", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, code, displayOrder } = body as { name?: string; code?: string; displayOrder?: number };
    if (!name?.trim()) {
      return NextResponse.json({ success: false, error: "name is required" }, { status: 400 });
    }
    const sector = await prisma.sector.create({
      data: {
        name: name.trim(),
        code: code?.trim() || null,
        displayOrder: typeof displayOrder === "number" ? displayOrder : 0,
      },
    });
    return NextResponse.json({
      success: true,
      data: { sector },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error creating sector:", error);
    return NextResponse.json(
      { success: false, error: "Failed to create sector", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

/** Seed sectors from PSX reference list (idempotent: only adds missing) */
export async function PUT(request: NextRequest) {
  try {
    const existing = await prisma.sector.findMany({ select: { name: true } });
    const existingNames = new Set(existing.map((s) => s.name));
    const toCreate = PSX_SECTORS.filter((s) => !existingNames.has(s.name));
    if (toCreate.length === 0) {
      return NextResponse.json({
        success: true,
        data: { seeded: 0, message: "All sectors already exist" },
        timestamp: new Date().toISOString(),
      });
    }
    await prisma.sector.createMany({
      data: toCreate.map((s) => ({
        name: s.name,
        code: s.code,
        displayOrder: s.displayOrder,
      })),
    });
    return NextResponse.json({
      success: true,
      data: { seeded: toCreate.length, sectors: toCreate.map((s) => s.name) },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error seeding sectors:", error);
    return NextResponse.json(
      { success: false, error: "Failed to seed sectors", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    await prisma.sector.delete({ where: { id } });
    return NextResponse.json({
      success: true,
      data: { deleted: id },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error deleting sector:", error);
    return NextResponse.json(
      { success: false, error: "Failed to delete sector", details: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

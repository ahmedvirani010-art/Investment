import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

type Body = {
  type: "ENTRY" | "EXIT";
  date: string;     // ISO date string
  price: number;
  quantity: number;
  fees?: number;
  notes?: string;
};

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = (await request.json()) as Body;
    const { type, date, price, quantity } = body;
    const fees = body.fees ?? 0;

    if (!type || !date || price == null || quantity == null || quantity <= 0) {
      return NextResponse.json(
        { success: false, error: "type, date, price, and quantity (>0) are required" },
        { status: 400 }
      );
    }
    if (type !== "ENTRY" && type !== "EXIT") {
      return NextResponse.json(
        { success: false, error: "type must be ENTRY or EXIT" },
        { status: 400 }
      );
    }

    const plan = await prisma.tradePlan.findUnique({
      where: { id },
      include: { stock: true },
    });
    if (!plan) {
      return NextResponse.json({ success: false, error: "Trade plan not found" }, { status: 404 });
    }

    if (type === "ENTRY" && plan.status !== "PLANNED" && plan.status !== "ACTIVE") {
      return NextResponse.json(
        { success: false, error: "Can only enter a PLANNED or ACTIVE trade plan" },
        { status: 400 }
      );
    }
    if (type === "EXIT" && plan.status !== "ACTIVE") {
      return NextResponse.json(
        { success: false, error: "Can only exit an ACTIVE trade plan" },
        { status: 400 }
      );
    }

    const dateObj = new Date(date);
    const txType = type === "ENTRY" ? "BUY" : "SELL";
    const amount = quantity * price;

    const result = await prisma.$transaction(async (tx) => {
      // 1. Create Position record linked to this plan
      const position = await tx.position.create({
        data: {
          tradePlanId: id,
          type,
          date: dateObj,
          price,
          quantity,
          fees,
          notes: body.notes ?? null,
        },
      });

      // 2. Create Transaction record (updates portfolio ledger)
      const transaction = await tx.transaction.create({
        data: {
          stockId: plan.stockId,
          type: txType,
          date: dateObj,
          quantity,
          price,
          amount,
          fees,
          notes: body.notes
            ? body.notes
            : `${type} — plan ${id.slice(0, 8)}`,
        },
      });

      // 3. Update UserStock holdings
      const existing = await tx.userStock.findUnique({
        where: { stockId: plan.stockId },
      });

      if (txType === "BUY") {
        if (!existing) {
          await tx.userStock.create({
            data: {
              stockId: plan.stockId,
              totalQuantity: quantity,
              averageCost: price,
              totalInvested: amount,
            },
          });
        } else {
          const newQty = existing.totalQuantity + quantity;
          const newInvested = existing.totalInvested + amount;
          await tx.userStock.update({
            where: { stockId: plan.stockId },
            data: {
              totalQuantity: newQty,
              totalInvested: newInvested,
              averageCost: newInvested / newQty,
            },
          });
        }
      } else {
        // SELL
        if (!existing || existing.totalQuantity < quantity) {
          throw new Error(
            `Insufficient quantity. Have ${existing?.totalQuantity ?? 0}, selling ${quantity}`
          );
        }
        const realizedGain = (price - existing.averageCost) * quantity;
        const newQty = existing.totalQuantity - quantity;
        const costReduction = existing.averageCost * quantity;
        const newInvested = Math.max(0, existing.totalInvested - costReduction);
        await tx.userStock.update({
          where: { stockId: plan.stockId },
          data: {
            totalQuantity: newQty,
            totalInvested: newInvested,
            averageCost: newQty > 0 ? newInvested / newQty : 0,
            realizedGain: existing.realizedGain + realizedGain,
          },
        });
      }

      // 4. Update plan status
      const newStatus = type === "ENTRY" ? "ACTIVE" : "CLOSED";
      await tx.tradePlan.update({
        where: { id },
        data: { status: newStatus },
      });

      // 5. For EXIT: create or update TradeJournal entry
      let journal = null;
      if (type === "EXIT") {
        // Find the first ENTRY position to get entry details
        const entryPosition = await tx.position.findFirst({
          where: { tradePlanId: id, type: "ENTRY" },
          orderBy: { date: "asc" },
        });

        const entryPrice = entryPosition?.price ?? plan.entryPrice;
        const entryDate = entryPosition?.date ?? plan.createdAt;
        const holdingDays = Math.round(
          (dateObj.getTime() - entryDate.getTime()) / (1000 * 60 * 60 * 24)
        );
        const realizedPL = (price - entryPrice) * quantity - fees;
        const realizedPLPercent = entryPrice > 0
          ? ((price - entryPrice) / entryPrice) * 100
          : 0;

        // Upsert journal (plan may already have one)
        const existingJournal = await tx.tradeJournal.findUnique({
          where: { tradePlanId: id },
        });

        if (existingJournal) {
          journal = await tx.tradeJournal.update({
            where: { tradePlanId: id },
            data: {
              exitDate: dateObj,
              exitPrice: price,
              realizedPL,
              realizedPLPercent,
              holdingPeriod: holdingDays,
              exitNotes: body.notes ?? null,
            },
          });
        } else {
          journal = await tx.tradeJournal.create({
            data: {
              tradePlanId: id,
              entryDate,
              exitDate: dateObj,
              entryPrice,
              exitPrice: price,
              quantity,
              realizedPL,
              realizedPLPercent,
              holdingPeriod: holdingDays,
              strategyLabel: null,
              exitNotes: body.notes ?? null,
            },
          });
        }
      }

      return { position, transaction, journal };
    });

    return NextResponse.json({
      success: true,
      data: {
        positionId: result.position.id,
        transactionId: result.transaction.id,
        journalId: result.journal?.id ?? null,
        planStatus: type === "ENTRY" ? "ACTIVE" : "CLOSED",
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error executing trade:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to execute trade",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

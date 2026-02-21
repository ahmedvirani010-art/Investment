import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";

type PostBody = {
  stockId: string;
  type: "BUY" | "SELL" | "CASH_DIVIDEND" | "BONUS_DIVIDEND";
  date: string; // ISO date
  quantity?: number;
  price?: number;
  amount?: number;
  fees?: number;
  notes?: string;
};

const VALID_TYPES = ["BUY", "SELL", "CASH_DIVIDEND", "BONUS_DIVIDEND"] as const;

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as PostBody;
    const { stockId, type, date, notes } = body;
    const fees = body.fees ?? 0;
    const dateObj = new Date(date);

    if (!stockId || !type || !date) {
      return NextResponse.json(
        { success: false, error: "Missing stockId, type, or date" },
        { status: 400 }
      );
    }
    const txType = type.toUpperCase() as (typeof VALID_TYPES)[number];
    if (!VALID_TYPES.includes(txType)) {
      return NextResponse.json(
        { success: false, error: "type must be BUY, SELL, CASH_DIVIDEND, or BONUS_DIVIDEND" },
        { status: 400 }
      );
    }

    const stock = await prisma.stock.findUnique({ where: { id: stockId } });
    if (!stock) {
      return NextResponse.json(
        { success: false, error: "Stock not found" },
        { status: 404 }
      );
    }

    let quantity: number;
    let price: number;
    let amount: number;

    if (txType === "CASH_DIVIDEND") {
      const amt = body.amount;
      const qty = body.quantity ?? 0;
      const pr = body.price ?? 0;
      if (amt != null && Number.isFinite(amt) && amt > 0) {
        amount = amt;
        quantity = qty >= 0 ? qty : 0;
        price = pr >= 0 ? pr : 0;
      } else if (qty > 0 && pr >= 0 && Number.isFinite(pr)) {
        amount = qty * pr;
        quantity = qty;
        price = pr;
      } else {
        return NextResponse.json(
          { success: false, error: "CASH_DIVIDEND requires amount > 0 or both quantity and price" },
          { status: 400 }
        );
      }
    } else if (txType === "BONUS_DIVIDEND") {
      const qty = body.quantity;
      if (qty == null || !Number.isFinite(qty) || qty <= 0) {
        return NextResponse.json(
          { success: false, error: "BONUS_DIVIDEND requires quantity > 0" },
          { status: 400 }
        );
      }
      quantity = qty;
      price = 0;
      amount = 0;
    } else {
      const q = body.quantity;
      const p = body.price;
      if (q == null || !Number.isFinite(q) || q <= 0 || p == null || !Number.isFinite(p) || p < 0) {
        return NextResponse.json(
          { success: false, error: "BUY/SELL require quantity (>0) and price (>=0)" },
          { status: 400 }
        );
      }
      quantity = q;
      price = p;
      amount = quantity * price;
    }

    const transaction = await prisma.transaction.create({
      data: {
        stockId,
        type: txType,
        date: dateObj,
        quantity,
        price,
        amount,
        fees: txType === "BONUS_DIVIDEND" ? 0 : fees,
        notes: notes ?? null,
      },
      include: {
        stock: { select: { ticker: true, name: true } },
      },
    });

    const existing = await prisma.userStock.findUnique({ where: { stockId } });

    if (txType === "BUY") {
      if (!existing) {
        await prisma.userStock.create({
          data: {
            stockId,
            totalQuantity: quantity,
            averageCost: price,
            totalInvested: amount,
          },
        });
      } else {
        const newTotalQuantity = existing.totalQuantity + quantity;
        const newTotalInvested = existing.totalInvested + amount;
        const newAverageCost = newTotalInvested / newTotalQuantity;
        await prisma.userStock.update({
          where: { stockId },
          data: {
            totalQuantity: newTotalQuantity,
            totalInvested: newTotalInvested,
            averageCost: newAverageCost,
          },
        });
      }
    } else if (txType === "SELL") {
      if (!existing || existing.totalQuantity < quantity) {
        return NextResponse.json(
          { success: false, error: "Insufficient quantity to sell" },
          { status: 400 }
        );
      }
      const realizedGain = (price - existing.averageCost) * quantity;
      const newTotalQuantity = existing.totalQuantity - quantity;
      const costReduction = existing.averageCost * quantity;
      const newTotalInvested = Math.max(0, existing.totalInvested - costReduction);
      const newAverageCost = newTotalQuantity > 0 ? newTotalInvested / newTotalQuantity : 0;

      await prisma.userStock.update({
        where: { stockId },
        data: {
          totalQuantity: newTotalQuantity,
          totalInvested: newTotalInvested,
          averageCost: newAverageCost,
          realizedGain: existing.realizedGain + realizedGain,
        },
      });
    } else if (txType === "CASH_DIVIDEND") {
      if (!existing) {
        await prisma.userStock.create({
          data: {
            stockId,
            totalQuantity: 0,
            totalInvested: 0,
            averageCost: 0,
            totalDividends: amount,
          },
        });
      } else {
        await prisma.userStock.update({
          where: { stockId },
          data: { totalDividends: { increment: amount } },
        });
      }
      await prisma.cashFlow.create({
        data: {
          date: dateObj,
          amount,
          notes: `Dividend: ${stock.ticker}`,
        },
      });
    } else if (txType === "BONUS_DIVIDEND") {
      if (!existing) {
        await prisma.userStock.create({
          data: {
            stockId,
            totalQuantity: quantity,
            totalInvested: 0,
            averageCost: 0,
          },
        });
      } else {
        const newTotalQuantity = existing.totalQuantity + quantity;
        const newAverageCost = newTotalQuantity > 0 ? existing.totalInvested / newTotalQuantity : 0;
        await prisma.userStock.update({
          where: { stockId },
          data: {
            totalQuantity: newTotalQuantity,
            averageCost: newAverageCost,
          },
        });
      }
    }

    return NextResponse.json({
      success: true,
      data: {
        transaction: {
          id: transaction.id,
          stockId: transaction.stockId,
          symbol: transaction.stock.ticker,
          name: transaction.stock.name,
          type: transaction.type,
          date: transaction.date,
          quantity: transaction.quantity,
          price: transaction.price,
          amount: transaction.amount,
          fees: transaction.fees,
          notes: transaction.notes,
        },
      },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error creating transaction:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to create transaction",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = request.nextUrl;
    const limit = searchParams.get("limit") || "50";
    const limitNum = Math.min(parseInt(limit, 10) || 50, 200);
    const type = searchParams.get("type"); // BUY, SELL, or undefined for all

    const where: { type?: string } = {};
    if (type) {
      where.type = type.toUpperCase();
    }

    const transactions = await prisma.transaction.findMany({
      where,
      include: {
        stock: {
          select: {
            ticker: true,
            name: true,
            sector: true,
          },
        },
      },
      orderBy: { date: "desc" },
      take: limitNum,
    });

    const enhanced = transactions.map((t) => ({
      id: t.id,
      stockId: t.stockId,
      symbol: t.stock.ticker,
      name: t.stock.name,
      sector: t.stock.sector,
      type: t.type,
      date: t.date,
      quantity: t.quantity,
      price: t.price,
      amount: t.amount,
      fees: t.fees,
      netAmount: t.amount - t.fees,
      notes: t.notes,
      createdAt: t.createdAt,
    }));

    const [totalCount, sumAmount, sumFees, buyCount, sellCount, buySum, sellSum] =
      await Promise.all([
        prisma.transaction.count({ where }),
        prisma.transaction.aggregate({ where, _sum: { amount: true } }),
        prisma.transaction.aggregate({ where, _sum: { fees: true } }),
        prisma.transaction.count({ where: { type: "BUY" } }),
        prisma.transaction.count({ where: { type: "SELL" } }),
        prisma.transaction.aggregate({
          where: { type: "BUY" },
          _sum: { amount: true },
        }),
        prisma.transaction.aggregate({
          where: { type: "SELL" },
          _sum: { amount: true },
        }),
      ]);

    const lastTx = await prisma.transaction.findFirst({
      orderBy: { date: "desc" },
      select: { date: true },
    });

    const summary = {
      totalCount,
      totalAmount: sumAmount._sum.amount ?? 0,
      totalFees: sumFees._sum.fees ?? 0,
      netAmount: (sumAmount._sum.amount ?? 0) - (sumFees._sum.fees ?? 0),
      buyCount,
      sellCount,
      buyAmount: buySum._sum.amount ?? 0,
      sellAmount: sellSum._sum.amount ?? 0,
      lastTransactionDate: lastTx?.date ?? null,
    };

    return NextResponse.json({
      success: true,
      data: { transactions: enhanced, summary },
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    console.error("Error fetching transactions:", error);
    return NextResponse.json(
      {
        success: false,
        error: "Failed to fetch transactions",
        details: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 }
    );
  }
}

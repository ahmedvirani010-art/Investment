-- CreateTable
CREATE TABLE "RiskSettings" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "accountValue" REAL NOT NULL,
    "maxRiskPerTradePct" REAL NOT NULL DEFAULT 2.0,
    "maxPositionSizePct" REAL NOT NULL DEFAULT 10.0,
    "maxTotalRiskPct" REAL NOT NULL DEFAULT 6.0,
    "maxSectorExposurePct" REAL NOT NULL DEFAULT 30.0,
    "maxSinglePositionPct" REAL NOT NULL DEFAULT 15.0,
    "minPositions" INTEGER NOT NULL DEFAULT 5,
    "maxPositions" INTEGER NOT NULL DEFAULT 20,
    "defaultStopLossPct" REAL NOT NULL DEFAULT 3.0,
    "minRewardRiskRatio" REAL NOT NULL DEFAULT 2.0,
    "useKellyCriterion" BOOLEAN NOT NULL DEFAULT false,
    "kellyFraction" REAL NOT NULL DEFAULT 0.25,
    "allowPyramiding" BOOLEAN NOT NULL DEFAULT true,
    "maxCorrelatedPositions" INTEGER NOT NULL DEFAULT 3,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "TradePlan" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "stockId" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "direction" TEXT NOT NULL,
    "entryPrice" REAL NOT NULL,
    "targetPrice" REAL,
    "stopLoss" REAL NOT NULL,
    "positionSize" REAL,
    "riskAmount" REAL,
    "rewardRiskRatio" REAL,
    "notes" TEXT,
    "checklist" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "TradePlan_stockId_fkey" FOREIGN KEY ("stockId") REFERENCES "Stock" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "Position" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "tradePlanId" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "date" DATETIME NOT NULL,
    "price" REAL NOT NULL,
    "quantity" REAL NOT NULL,
    "fees" REAL NOT NULL DEFAULT 0,
    "notes" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "Position_tradePlanId_fkey" FOREIGN KEY ("tradePlanId") REFERENCES "TradePlan" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "TradeJournal" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "tradePlanId" TEXT NOT NULL,
    "entryDate" DATETIME NOT NULL,
    "exitDate" DATETIME,
    "entryPrice" REAL NOT NULL,
    "exitPrice" REAL,
    "quantity" REAL NOT NULL,
    "realizedPL" REAL,
    "realizedPLPercent" REAL,
    "holdingPeriod" INTEGER,
    "strategyLabel" TEXT,
    "ideaSource" TEXT,
    "exitMethod" TEXT,
    "entryNotes" TEXT,
    "exitNotes" TEXT,
    "chartImage" TEXT,
    "emotionalState" TEXT,
    "lessonsLearned" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "TradeJournal_tradePlanId_fkey" FOREIGN KEY ("tradePlanId") REFERENCES "TradePlan" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "AccountSnapshot" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "date" DATETIME NOT NULL,
    "totalValue" REAL NOT NULL,
    "cashBalance" REAL NOT NULL,
    "investedValue" REAL NOT NULL,
    "unrealizedPL" REAL NOT NULL,
    "realizedPL" REAL NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "LlmSettings" (
    "id" TEXT NOT NULL PRIMARY KEY DEFAULT 'singleton',
    "apiKey" TEXT NOT NULL,
    "model" TEXT NOT NULL DEFAULT 'openai/gpt-4o-mini',
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateIndex
CREATE INDEX "TradePlan_stockId_idx" ON "TradePlan"("stockId");

-- CreateIndex
CREATE INDEX "TradePlan_status_idx" ON "TradePlan"("status");

-- CreateIndex
CREATE INDEX "Position_tradePlanId_idx" ON "Position"("tradePlanId");

-- CreateIndex
CREATE UNIQUE INDEX "TradeJournal_tradePlanId_key" ON "TradeJournal"("tradePlanId");

-- CreateIndex
CREATE INDEX "TradeJournal_entryDate_idx" ON "TradeJournal"("entryDate");

-- CreateIndex
CREATE INDEX "TradeJournal_strategyLabel_idx" ON "TradeJournal"("strategyLabel");

-- CreateIndex
CREATE UNIQUE INDEX "AccountSnapshot_date_key" ON "AccountSnapshot"("date");

-- CreateIndex
CREATE INDEX "AccountSnapshot_date_idx" ON "AccountSnapshot"("date");

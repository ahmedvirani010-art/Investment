"use client";

import { useState, useEffect, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

type Stock = { id: string; ticker: string; name: string; sector: string };

/** Predefined PSX stocks for dropdown (ticker, name, sector) */
const PSX_STOCK_OPTIONS: { ticker: string; name: string; sector: string }[] = [
  { ticker: "HBL", name: "Habib Bank Limited", sector: "Banks" },
  { ticker: "UBL", name: "United Bank Limited", sector: "Banks" },
  { ticker: "MCB", name: "MCB Bank Limited", sector: "Banks" },
  { ticker: "BAFL", name: "Bank Alfalah Limited", sector: "Banks" },
  { ticker: "ABL", name: "Allied Bank Limited", sector: "Banks" },
  { ticker: "PSO", name: "Pakistan State Oil", sector: "Oil & Gas" },
  { ticker: "OGDC", name: "Oil & Gas Development Company", sector: "Oil & Gas" },
  { ticker: "PPL", name: "Pakistan Petroleum Limited", sector: "Oil & Gas" },
  { ticker: "POL", name: "Pakistan Oilfields Limited", sector: "Oil & Gas" },
  { ticker: "LUCK", name: "Lucky Cement Limited", sector: "Cement" },
  { ticker: "DGKC", name: "D.G. Khan Cement Company", sector: "Cement" },
  { ticker: "MLCF", name: "Maple Leaf Cement Factory", sector: "Cement" },
  { ticker: "FFC", name: "Fauji Fertilizer Company", sector: "Fertilizer" },
  { ticker: "EFERT", name: "Engro Fertilizers Limited", sector: "Fertilizer" },
  { ticker: "HUBC", name: "Hub Power Company", sector: "Power" },
  { ticker: "ENGRO", name: "Engro Corporation Limited", sector: "Chemicals" },
  { ticker: "NESTLE", name: "Nestle Pakistan Limited", sector: "Food & Personal Care" },
  { ticker: "INDU", name: "Indus Motor Company", sector: "Automobiles" },
  { ticker: "PSMC", name: "Pak Suzuki Motor Company", sector: "Automobiles" },
  { ticker: "TRG", name: "The Resource Group", sector: "Technology" },
  { ticker: "SYS", name: "Systems Limited", sector: "Technology" },
  { ticker: "PTCL", name: "Pakistan Telecommunication Company", sector: "Technology" },
  { ticker: "NML", name: "Nishat Mills Limited", sector: "Textile" },
  { ticker: "PTC", name: "Pakistan Tobacco Company", sector: "Miscellaneous" },
  { ticker: "UNILEVER", name: "Unilever Pakistan Limited", sector: "Miscellaneous" },
];

const SECTOR_OPTIONS = Array.from(new Set(PSX_STOCK_OPTIONS.map((s) => s.sector))).sort();

type PlanOption = { id: string; symbol: string; name: string; status: string; direction: string };

export function AddTransactionForm({
  onSuccess,
  embedded = false,
}: { onSuccess?: () => void; embedded?: boolean }) {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loadingStocks, setLoadingStocks] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [stockId, setStockId] = useState("");
  const [type, setType] = useState<"BUY" | "SELL" | "DEPOSIT" | "CASH_DIVIDEND" | "BONUS_DIVIDEND">("BUY");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [amount, setAmount] = useState("");
  const [fees, setFees] = useState("");
  const [notes, setNotes] = useState("");
  const [tradePlanId, setTradePlanId] = useState("");
  const [plansForStock, setPlansForStock] = useState<PlanOption[]>([]);
  const isDeposit = type === "DEPOSIT";
  const isDividend = type === "CASH_DIVIDEND" || type === "BONUS_DIVIDEND";
  const isCashDividend = type === "CASH_DIVIDEND";
  const isBonusDividend = type === "BONUS_DIVIDEND";

  useEffect(() => {
    fetch("/api/stocks")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.stocks) {
          setStocks(res.data.stocks);
          if (res.data.stocks.length > 0 && !stockId) {
            setStockId(res.data.stocks[0].id);
          }
        }
      })
      .finally(() => setLoadingStocks(false));
  }, []);

  // Fetch trade plans for selected stock when BUY/SELL only
  useEffect(() => {
    if (isDeposit || isDividend || !stockId) {
      setPlansForStock([]);
      setTradePlanId("");
      return;
    }
    const statuses = type === "BUY" ? ["PLANNED", "ACTIVE"] : ["ACTIVE"];
    Promise.all(
      statuses.map((s) =>
        fetch(`/api/portfolio/plans?stockId=${encodeURIComponent(stockId)}&status=${s}`).then((r) => r.json())
      )
    )
      .then((results) => {
        const seen = new Set<string>();
        const combined: PlanOption[] = [];
        for (const res of results) {
          if (res.success && res.data?.plans) {
            for (const p of res.data.plans) {
              if (!seen.has(p.id)) {
                seen.add(p.id);
                combined.push({
                  id: p.id,
                  symbol: p.symbol,
                  name: p.name,
                  status: p.status,
                  direction: p.direction,
                });
              }
            }
          }
        }
        setPlansForStock(combined);
        setTradePlanId((prev) => (combined.some((p) => p.id === prev) ? prev : ""));
      })
      .catch(() => setPlansForStock([]));
  }, [stockId, type, isDeposit, isDividend]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isDeposit) {
      const amt = parseFloat(amount);
      if (!date || !Number.isFinite(amt) || amt <= 0) {
        toast.error("Enter date and amount (Rs) > 0.");
        return;
      }
      setSubmitting(true);
      try {
        const res = await fetch("/api/portfolio/cash-flow", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            date: new Date(date).toISOString(),
            amount: amt,
            notes: notes.trim() || undefined,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          toast.error(data.error ?? "Failed to add cash");
          return;
        }
        toast.success(`Added Rs ${amt.toLocaleString("en-PK", { maximumFractionDigits: 0 })}. Account value updated.`);
        setAmount("");
        setNotes("");
        onSuccess?.();
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Request failed");
      } finally {
        setSubmitting(false);
      }
      return;
    }

    if (isCashDividend) {
      const amt = parseFloat(amount);
      if (!stockId || !date || !Number.isFinite(amt) || amt <= 0) {
        toast.error("Please fill stock, date, and amount (Rs) > 0.");
        return;
      }
      setSubmitting(true);
      try {
        const res = await fetch("/api/portfolio/transactions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            stockId,
            type: "CASH_DIVIDEND",
            date: new Date(date).toISOString(),
            amount: amt,
            quantity: quantity ? parseFloat(quantity) : undefined,
            price: price ? parseFloat(price) : undefined,
            notes: notes.trim() || undefined,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          toast.error(data.error ?? "Failed to add transaction");
          return;
        }
        toast.success("Cash dividend recorded");
        setAmount("");
        setQuantity("");
        setPrice("");
        setNotes("");
        onSuccess?.();
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Request failed");
      } finally {
        setSubmitting(false);
      }
      return;
    }

    if (isBonusDividend) {
      const q = parseFloat(quantity);
      if (!stockId || !date || !Number.isFinite(q) || q <= 0) {
        toast.error("Please fill stock, date, and quantity (bonus shares) > 0.");
        return;
      }
      setSubmitting(true);
      try {
        const res = await fetch("/api/portfolio/transactions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            stockId,
            type: "BONUS_DIVIDEND",
            date: new Date(date).toISOString(),
            quantity: q,
            notes: notes.trim() || undefined,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          toast.error(data.error ?? "Failed to add transaction");
          return;
        }
        toast.success("Bonus dividend recorded");
        setQuantity("");
        setNotes("");
        onSuccess?.();
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Request failed");
      } finally {
        setSubmitting(false);
      }
      return;
    }

    const q = parseFloat(quantity);
    const p = parseFloat(price);
    const f = fees ? parseFloat(fees) : 0;
    if (!stockId || !date || !Number.isFinite(q) || q <= 0 || !Number.isFinite(p) || p < 0) {
      toast.error("Please fill stock, date, quantity (>0), and price (≥0).");
      return;
    }
    setSubmitting(true);
    try {
      if (tradePlanId) {
        const res = await fetch(`/api/portfolio/plans/${tradePlanId}/execute`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type: type === "BUY" ? "ENTRY" : "EXIT",
            date: new Date(date).toISOString(),
            price: p,
            quantity: q,
            fees: Number.isFinite(f) ? f : 0,
            notes: notes.trim() || undefined,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          toast.error(data.error ?? "Failed to execute trade plan");
          return;
        }
        toast.success("Trade executed and linked to plan");
      } else {
        const res = await fetch("/api/portfolio/transactions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            stockId,
            type,
            date: new Date(date).toISOString(),
            quantity: q,
            price: p,
            fees: Number.isFinite(f) ? f : 0,
            notes: notes.trim() || undefined,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          toast.error(data.error ?? "Failed to add transaction");
          return;
        }
        toast.success("Transaction added");
      }
      setQuantity("");
      setPrice("");
      setFees("");
      setNotes("");
      setTradePlanId("");
      onSuccess?.();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingStocks) {
    return embedded ? (
      <p className="text-sm text-muted-foreground py-4">Loading stocks…</p>
    ) : (
      <Card>
        <CardHeader>
          <CardTitle>Add transaction</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Loading stocks…</p>
        </CardContent>
      </Card>
    );
  }

  if (stocks.length === 0) {
    return embedded ? (
      <div className="space-y-4">
        <p className="text-sm text-muted-foreground">
          No stocks in the database. Add a stock first via the &quot;Add stock&quot; form below.
        </p>
        <AddStockForm onAdded={() => {
          fetch("/api/stocks")
            .then((r) => r.json())
            .then((res) => {
              if (res.success && res.data?.stocks) {
                setStocks(res.data.stocks);
                if (res.data.stocks[0]) setStockId(res.data.stocks[0].id);
              }
            });
        }} />
      </div>
    ) : (
      <Card>
        <CardHeader>
          <CardTitle>Add transaction</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No stocks in the database. Add a stock first via the &quot;Add stock&quot; form below.
          </p>
          <AddStockForm onAdded={() => {
            fetch("/api/stocks")
              .then((r) => r.json())
              .then((res) => {
                if (res.success && res.data?.stocks) {
                  setStocks(res.data.stocks);
                  if (res.data.stocks[0]) setStockId(res.data.stocks[0].id);
                }
              });
          }} />
        </CardContent>
      </Card>
    );
  }

  const formContent = (
    <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {!isDeposit && (
              <div className="space-y-2">
                <Label>Stock</Label>
                <Select value={stockId} onValueChange={setStockId}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select stock" />
                  </SelectTrigger>
                  <SelectContent>
                    {stocks.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.ticker} – {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-2">
              <Label>Type</Label>
              <Select value={type} onValueChange={(v) => setType(v as "BUY" | "SELL" | "DEPOSIT" | "CASH_DIVIDEND" | "BONUS_DIVIDEND")}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="BUY">BUY</SelectItem>
                  <SelectItem value="SELL">SELL</SelectItem>
                  <SelectItem value="CASH_DIVIDEND">Cash dividend</SelectItem>
                  <SelectItem value="BONUS_DIVIDEND">Bonus dividend</SelectItem>
                  <SelectItem value="DEPOSIT">Add cash (deposit)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          {!isDeposit && !isDividend && plansForStock.length > 0 && (
            <div className="space-y-2">
              <Label>Link to trade plan (optional)</Label>
              <Select value={tradePlanId} onValueChange={setTradePlanId}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="None — add as standalone transaction" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">None — add as standalone transaction</SelectItem>
                  {plansForStock.map((plan) => (
                    <SelectItem key={plan.id} value={plan.id}>
                      {plan.symbol} — {plan.status} {plan.direction}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="tx-date">Date</Label>
              <Input
                id="tx-date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
            {isDeposit || isCashDividend ? (
              <div className="space-y-2">
                <Label htmlFor="tx-amount">Amount (Rs)</Label>
                <Input
                  id="tx-amount"
                  type="number"
                  min="0.01"
                  step="any"
                  placeholder={isCashDividend ? "e.g. 500" : "e.g. 50000"}
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="tx-quantity">{isBonusDividend ? "Bonus shares" : "Quantity"}</Label>
                <Input
                  id="tx-quantity"
                  type="number"
                  min="0.0001"
                  step="any"
                  placeholder={isBonusDividend ? "e.g. 10" : "e.g. 100"}
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                />
              </div>
            )}
          </div>
          {isCashDividend && (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="tx-qty-ref">Shares (optional)</Label>
                <Input
                  id="tx-qty-ref"
                  type="number"
                  min="0"
                  step="any"
                  placeholder="e.g. 100"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tx-price-ref">Per share (Rs, optional)</Label>
                <Input
                  id="tx-price-ref"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="e.g. 5"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
              </div>
            </div>
          )}
          {!isDeposit && !isDividend && (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="tx-price">Price (Rs)</Label>
                <Input
                  id="tx-price"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="e.g. 150.50"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="tx-fees">Fees (Rs, optional)</Label>
                <Input
                  id="tx-fees"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0"
                  value={fees}
                  onChange={(e) => setFees(e.target.value)}
                />
              </div>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="tx-notes">Notes (optional)</Label>
            <Input
              id="tx-notes"
              type="text"
              placeholder={isDeposit ? "e.g. Salary, bonus, transfer" : "Optional notes"}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
          <Button type="submit" disabled={submitting}>
            {submitting
              ? "Adding…"
              : isDeposit
                ? "Add cash"
                : isCashDividend
                  ? "Record cash dividend"
                  : isBonusDividend
                    ? "Record bonus dividend"
                    : "Add transaction"}
          </Button>
        </form>
  );

  if (embedded) return formContent;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Add transaction</CardTitle>
        <p className="text-sm text-muted-foreground">
          Record a buy, sell, cash or bonus dividend, or add cash (deposit). Cash updates account value for position sizing.
        </p>
      </CardHeader>
      <CardContent>{formContent}</CardContent>
    </Card>
  );
}

function AddStockForm({ onAdded }: { onAdded: () => void }) {
  const [sector, setSector] = useState("");
  const [selectedTicker, setSelectedTicker] = useState("");
  const [customMode, setCustomMode] = useState(false);
  const [customTicker, setCustomTicker] = useState("");
  const [customName, setCustomName] = useState("");
  const [customSector, setCustomSector] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const stocksBySector = useMemo(
    () =>
      sector
        ? PSX_STOCK_OPTIONS.filter((s) => s.sector === sector)
        : PSX_STOCK_OPTIONS,
    [sector]
  );

  const selectedStock = selectedTicker
    ? PSX_STOCK_OPTIONS.find((s) => s.ticker === selectedTicker)
    : null;

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const tickerVal = customMode ? customTicker.trim().toUpperCase() : selectedStock?.ticker ?? "";
    const nameVal = customMode ? customName.trim() : selectedStock?.name ?? "";
    const sectorVal = customMode ? customSector.trim() : selectedStock?.sector ?? "";
    if (!tickerVal || !nameVal || !sectorVal) {
      toast.error("Please select a stock or fill Ticker, Name, and Sector.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch("/api/stocks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ticker: tickerVal,
          name: nameVal,
          sector: sectorVal,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        toast.error(data.error ?? "Failed to add stock");
        return;
      }
      toast.success("Stock added");
      setSector("");
      setSelectedTicker("");
      setCustomMode(false);
      setCustomTicker("");
      setCustomName("");
      setCustomSector("");
      onAdded();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Request failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleAdd} className="mt-4 space-y-3 rounded-md border p-4">
      <p className="text-sm font-medium">Add new stock</p>

      {!customMode ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <Label>Sector</Label>
              <Select value={sector || "__all__"} onValueChange={(v) => { setSector(v === "__all__" ? "" : v); setSelectedTicker(""); }}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="All sectors" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All sectors</SelectItem>
                  {SECTOR_OPTIONS.map((sec) => (
                    <SelectItem key={sec} value={sec}>
                      {sec}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label>Ticker – Name</Label>
              <Select value={selectedTicker} onValueChange={setSelectedTicker}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select stock" />
                </SelectTrigger>
                <SelectContent>
                  {stocksBySector.map((s) => (
                    <SelectItem key={s.ticker} value={s.ticker}>
                      {s.ticker} – {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          {selectedStock && (
            <p className="text-xs text-muted-foreground">
              Selected: {selectedStock.ticker} | {selectedStock.name} | {selectedStock.sector}
            </p>
          )}
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={submitting || !selectedTicker}>
              {submitting ? "Adding…" : "Add stock"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setCustomMode(true)}
            >
              Custom / Other
            </Button>
          </div>
        </>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <Label htmlFor="new-ticker">Ticker</Label>
              <Input
                id="new-ticker"
                placeholder="e.g. HBL"
                value={customTicker}
                onChange={(e) => setCustomTicker(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="new-name">Name</Label>
              <Input
                id="new-name"
                placeholder="e.g. Habib Bank Limited"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="new-sector">Sector</Label>
              <Select value={customSector} onValueChange={setCustomSector}>
                <SelectTrigger id="new-sector" className="w-full">
                  <SelectValue placeholder="Select sector" />
                </SelectTrigger>
                <SelectContent>
                  {SECTOR_OPTIONS.map((sec) => (
                    <SelectItem key={sec} value={sec}>
                      {sec}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={submitting}>
              {submitting ? "Adding…" : "Add stock"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => setCustomMode(false)}
            >
              Back to list
            </Button>
          </div>
        </>
      )}
    </form>
  );
}

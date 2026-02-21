"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

type StockOption = { id: string; ticker: string; name: string; sector: string };

type WatchlistItemRow = {
  id: string;
  stockId: string;
  notes: string | null;
  targetPrice: number | null;
  createdAt: string;
  stock: {
    id: string;
    ticker: string;
    name: string;
    sector: string;
    lastPrice: number | null;
  };
};

export function WatchlistContent() {
  const [items, setItems] = useState<WatchlistItemRow[]>([]);
  const [stocks, setStocks] = useState<StockOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [addOpen, setAddOpen] = useState(false);
  const [addStockId, setAddStockId] = useState("");
  const [addNotes, setAddNotes] = useState("");
  const [addTargetPrice, setAddTargetPrice] = useState("");
  const [addSubmitting, setAddSubmitting] = useState(false);
  const [editingItem, setEditingItem] = useState<WatchlistItemRow | null>(null);
  const [editNotes, setEditNotes] = useState("");
  const [editTargetPrice, setEditTargetPrice] = useState("");
  const [editSubmitting, setEditSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [refreshPricesLoading, setRefreshPricesLoading] = useState(false);

  const loadWatchlist = useCallback(() => {
    fetch("/api/watchlist")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.items) {
          setItems(res.data.items);
        } else {
          toast.error(res.error ?? "Failed to load watchlist");
        }
      })
      .catch(() => toast.error("Request failed"))
      .finally(() => setLoading(false));
  }, []);

  const loadStocks = useCallback(() => {
    fetch("/api/stocks")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.stocks) {
          setStocks(res.data.stocks);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadWatchlist();
  }, [loadWatchlist]);

  useEffect(() => {
    if (addOpen) {
      loadStocks();
      setAddStockId("");
      setAddNotes("");
      setAddTargetPrice("");
    }
  }, [addOpen, loadStocks]);

  const handleRefreshPrices = () => {
    setRefreshPricesLoading(true);
    fetch("/api/prices/sync", { method: "POST" })
      .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
      .then(({ ok, data: res }) => {
        if (ok && res.success && res.data) {
          const { updated, errors, total } = res.data;
          if (errors?.length > 0) {
            const failedTickers = errors.map((e: { ticker: string; error: string }) => e.ticker).join(", ");
            toast.warning(
              `Prices updated: ${updated}/${total}. ${errors.length} failed: ${failedTickers}`,
              { duration: 12000 }
            );
          } else {
            toast.success(`Prices updated for ${updated} stock${updated !== 1 ? "s" : ""}.`);
          }
          loadWatchlist();
        } else {
          const msg = res?.details ?? res?.error ?? "Failed to refresh prices";
          toast.error(msg);
        }
      })
      .catch(() => toast.error("Failed to refresh prices"))
      .finally(() => setRefreshPricesLoading(false));
  };

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!addStockId) {
      toast.error("Select a stock");
      return;
    }
    setAddSubmitting(true);
    fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        stockId: addStockId,
        notes: addNotes.trim() || undefined,
        targetPrice: addTargetPrice.trim() ? parseFloat(addTargetPrice) : undefined,
      }),
    })
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          toast.success("Added to watchlist");
          setAddOpen(false);
          loadWatchlist();
        } else {
          toast.error(res.error ?? "Failed to add");
        }
      })
      .catch(() => toast.error("Request failed"))
      .finally(() => setAddSubmitting(false));
  };

  const openEdit = (item: WatchlistItemRow) => {
    setEditingItem(item);
    setEditNotes(item.notes ?? "");
    setEditTargetPrice(item.targetPrice != null ? String(item.targetPrice) : "");
  };

  const handleEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingItem) return;
    setEditSubmitting(true);
    fetch(`/api/watchlist/${editingItem.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        notes: editNotes.trim() || null,
        targetPrice: editTargetPrice.trim() ? parseFloat(editTargetPrice) : null,
      }),
    })
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          toast.success("Updated");
          setEditingItem(null);
          loadWatchlist();
        } else {
          toast.error(res.error ?? "Failed to update");
        }
      })
      .catch(() => toast.error("Request failed"))
      .finally(() => setEditSubmitting(false));
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remove this stock from your watchlist?")) return;
    setDeletingId(id);
    try {
      const res = await fetch(`/api/watchlist/${id}`, { method: "DELETE" });
      const json = await res.json();
      if (json.success) {
        setItems((prev) => prev.filter((i) => i.id !== id));
        toast.success("Removed from watchlist");
      } else {
        toast.error(json.error ?? "Failed to remove");
      }
    } catch {
      toast.error("Request failed");
    } finally {
      setDeletingId(null);
    }
  };

  const watchlistedStockIds = new Set(items.map((i) => i.stockId));
  const stocksAvailableToAdd = stocks.filter((s) => !watchlistedStockIds.has(s.id));

  if (loading) {
    return (
      <Card>
        <CardContent className="py-8">
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Watchlist</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {items.length} stock{items.length !== 1 ? "s" : ""} · track prices and notes
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={refreshPricesLoading}
              onClick={handleRefreshPrices}
            >
              {refreshPricesLoading ? "Updating…" : "Refresh prices"}
            </Button>
            <Button onClick={() => setAddOpen(true)}>+ Add to watchlist</Button>
          </div>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">
              No stocks on your watchlist yet. Add one to track price and notes.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticker</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Sector</TableHead>
                  <TableHead className="text-right">Last Price</TableHead>
                  <TableHead className="text-right">Target Price</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead className="text-muted-foreground">Added</TableHead>
                  <TableHead className="w-[120px]" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="font-medium">
                      <Link
                        href={`/dashboard/stock/${row.stock.ticker}`}
                        className="text-primary hover:underline"
                      >
                        {row.stock.ticker}
                      </Link>
                    </TableCell>
                    <TableCell className="max-w-[180px] truncate" title={row.stock.name}>
                      <Link
                        href={`/dashboard/stock/${row.stock.ticker}`}
                        className="text-foreground hover:underline truncate block"
                      >
                        {row.stock.name}
                      </Link>
                    </TableCell>
                    <TableCell>{row.stock.sector}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {row.stock.lastPrice != null
                        ? row.stock.lastPrice.toFixed(2)
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {row.targetPrice != null ? row.targetPrice.toFixed(2) : "—"}
                    </TableCell>
                    <TableCell className="max-w-[160px] truncate text-muted-foreground" title={row.notes ?? ""}>
                      {row.notes ?? "—"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {new Date(row.createdAt).toLocaleDateString()}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1 justify-end">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 px-2 text-xs"
                          onClick={() => openEdit(row)}
                        >
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                          disabled={deletingId === row.id}
                          onClick={() => handleDelete(row.id)}
                        >
                          {deletingId === row.id ? "…" : "Remove"}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add to watchlist dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add to watchlist</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAdd} className="space-y-4">
            <div className="space-y-2">
              <Label>Stock</Label>
              <Select value={addStockId} onValueChange={setAddStockId} required>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select a stock" />
                </SelectTrigger>
                <SelectContent>
                  {stocksAvailableToAdd.length === 0 ? (
                    <div className="py-4 text-center text-sm text-muted-foreground">
                      No stocks left to add (all are on the watchlist).
                    </div>
                  ) : (
                    stocksAvailableToAdd.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.ticker} — {s.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="add-notes">Notes (optional)</Label>
              <Input
                id="add-notes"
                value={addNotes}
                onChange={(e) => setAddNotes(e.target.value)}
                placeholder="e.g. Waiting for breakout"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="add-target">Target price (optional)</Label>
              <Input
                id="add-target"
                type="number"
                step="any"
                min="0"
                value={addTargetPrice}
                onChange={(e) => setAddTargetPrice(e.target.value)}
                placeholder="e.g. 150"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAddOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={addSubmitting || !addStockId || stocksAvailableToAdd.length === 0}>
                {addSubmitting ? "Adding…" : "Add"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit watchlist item dialog */}
      <Dialog open={!!editingItem} onOpenChange={(open) => !open && setEditingItem(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Edit {editingItem?.stock.ticker}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEdit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="edit-notes">Notes</Label>
              <Input
                id="edit-notes"
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                placeholder="Optional notes"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-target">Target price</Label>
              <Input
                id="edit-target"
                type="number"
                step="any"
                min="0"
                value={editTargetPrice}
                onChange={(e) => setEditTargetPrice(e.target.value)}
                placeholder="Optional target"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditingItem(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={editSubmitting}>
                {editSubmitting ? "Saving…" : "Save"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

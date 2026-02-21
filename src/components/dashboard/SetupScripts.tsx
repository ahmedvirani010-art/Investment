"use client";

import { useState, useEffect } from "react";
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
import { toast } from "sonner";

type Stock = { id: string; ticker: string; name: string; sector: string };
type Sector = { id: string; name: string };

export function SetupScripts() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [sectorFilter, setSectorFilter] = useState<string>("");
  const [newTicker, setNewTicker] = useState("");
  const [newName, setNewName] = useState("");
  const [newSector, setNewSector] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchScripts = () => {
    const q = sectorFilter ? `?sector=${encodeURIComponent(sectorFilter)}` : "";
    fetch(`/api/setup/scripts${q}`)
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.stocks) setStocks(res.data.stocks);
        else toast.error(res.error ?? "Failed to load scripts");
      })
      .catch(() => toast.error("Request failed"));
  };

  const fetchSectors = () => {
    fetch("/api/setup/sectors")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.sectors) setSectors(res.data.sectors);
      })
      .catch(() => {});
  };

  useEffect(() => {
    setLoading(true);
    fetchSectors();
    fetch("/api/setup/scripts")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.stocks) setStocks(res.data.stocks);
        else toast.error(res.error ?? "Failed to load scripts");
      })
      .catch(() => toast.error("Request failed"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!loading) fetchScripts();
  }, [sectorFilter, loading]);

  const handleImportPSX = () => {
    setImporting(true);
    fetch("/api/setup/scripts", { method: "PUT" })
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          toast.success(res.data.imported ? `Imported ${res.data.imported} scripts` : "All scripts already imported");
          fetchScripts();
        } else toast.error(res.error ?? "Failed to import");
      })
      .catch(() => toast.error("Request failed"))
      .finally(() => setImporting(false));
  };

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTicker.trim() || !newName.trim() || !newSector) {
      toast.error("Ticker, name, and sector are required");
      return;
    }
    setSubmitting(true);
    fetch("/api/setup/scripts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticker: newTicker.trim().toUpperCase(),
        name: newName.trim(),
        sector: newSector,
      }),
    })
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          toast.success("Script added");
          setNewTicker("");
          setNewName("");
          fetchScripts();
        } else toast.error(res.error ?? "Failed to add");
      })
      .catch(() => toast.error("Request failed"))
      .finally(() => setSubmitting(false));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>PSX scripts (stocks)</CardTitle>
          <p className="text-sm text-muted-foreground">
            Import full PSX script list or add scripts manually.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleImportPSX} disabled={importing} variant="outline">
              {importing ? "Importing…" : "Import PSX script list"}
            </Button>
          </div>
          <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label htmlFor="script-ticker">Ticker</Label>
              <Input
                id="script-ticker"
                placeholder="e.g. HBL"
                value={newTicker}
                onChange={(e) => setNewTicker(e.target.value)}
                className="w-28"
              />
            </div>
            <div className="space-y-2 min-w-[200px]">
              <Label htmlFor="script-name">Name</Label>
              <Input
                id="script-name"
                placeholder="Company name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="space-y-2 min-w-[180px]">
              <Label>Sector</Label>
              <Select value={newSector} onValueChange={setNewSector}>
                <SelectTrigger>
                  <SelectValue placeholder="Select sector" />
                </SelectTrigger>
                <SelectContent>
                  {sectors.map((s) => (
                    <SelectItem key={s.id} value={s.name}>
                      {s.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" disabled={submitting || sectors.length === 0}>
              {submitting ? "Adding…" : "Add script"}
            </Button>
          </form>
          {sectors.length === 0 && (
            <p className="text-sm text-amber-600 dark:text-amber-500">
              Add sectors first (Setup → Sectors → Load PSX sector list).
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Current scripts ({stocks.length})</CardTitle>
          <div className="flex gap-2 mt-2">
            <Select value={sectorFilter || "__all__"} onValueChange={(v) => setSectorFilter(v === "__all__" ? "" : v)}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="All sectors" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All sectors</SelectItem>
                {sectors.map((s) => (
                  <SelectItem key={s.id} value={s.name}>
                    {s.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : stocks.length === 0 ? (
            <p className="text-sm text-muted-foreground">No scripts. Import PSX list or add manually.</p>
          ) : (
            <div className="max-h-[400px] overflow-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Sector</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {stocks.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium">{s.ticker}</TableCell>
                      <TableCell className="max-w-[300px] truncate">{s.name}</TableCell>
                      <TableCell className="text-muted-foreground">{s.sector}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";

type Sector = { id: string; name: string; code: string | null; displayOrder: number };

export function SetupSectors() {
  const [sectors, setSectors] = useState<Sector[]>([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [newName, setNewName] = useState("");
  const [newCode, setNewCode] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const fetchSectors = () => {
    setLoading(true);
    fetch("/api/setup/sectors")
      .then((r) => r.json())
      .then((res) => {
        if (res.success && res.data?.sectors) setSectors(res.data.sectors);
        else toast.error(res.error ?? "Failed to load sectors");
      })
      .catch(() => toast.error("Request failed"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSectors();
  }, []);

  const handleLoadPSX = () => {
    setSeeding(true);
    fetch("/api/setup/sectors", { method: "PUT" })
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          toast.success(res.data.seeded ? `Loaded ${res.data.seeded} sectors` : "All sectors already loaded");
          fetchSectors();
        } else toast.error(res.error ?? "Failed to load PSX sectors");
      })
      .catch(() => toast.error("Request failed"))
      .finally(() => setSeeding(false));
  };

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) {
      toast.error("Sector name is required");
      return;
    }
    setSubmitting(true);
    fetch("/api/setup/sectors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newName.trim(), code: newCode.trim() || undefined }),
    })
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          toast.success("Sector added");
          setNewName("");
          setNewCode("");
          fetchSectors();
        } else toast.error(res.error ?? "Failed to add");
      })
      .catch(() => toast.error("Request failed"))
      .finally(() => setSubmitting(false));
  };

  const handleDelete = (id: string) => {
    if (!confirm("Delete this sector?")) return;
    fetch(`/api/setup/sectors/${id}`, { method: "DELETE" })
      .then((r) => r.json())
      .then((res) => {
        if (res.success) {
          toast.success("Sector deleted");
          fetchSectors();
        } else toast.error(res.error ?? "Failed to delete");
      })
      .catch(() => toast.error("Request failed"));
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>PSX sectors</CardTitle>
          <p className="text-sm text-muted-foreground">
            Load official PSX sector list or add sectors manually.
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Button onClick={handleLoadPSX} disabled={seeding} variant="outline">
              {seeding ? "Loading…" : "Load PSX sector list"}
            </Button>
          </div>
          <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-4">
            <div className="space-y-2">
              <Label htmlFor="sector-name">Name</Label>
              <Input
                id="sector-name"
                placeholder="e.g. Banks"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-48"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sector-code">Code (optional)</Label>
              <Input
                id="sector-code"
                placeholder="e.g. BANKS"
                value={newCode}
                onChange={(e) => setNewCode(e.target.value)}
                className="w-32"
              />
            </div>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Adding…" : "Add sector"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Current sectors ({sectors.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : sectors.length === 0 ? (
            <p className="text-sm text-muted-foreground">No sectors. Load PSX list or add manually.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead className="w-24">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sectors.map((s) => (
                  <TableRow key={s.id}>
                    <TableCell className="font-medium">{s.name}</TableCell>
                    <TableCell className="text-muted-foreground">{s.code ?? "—"}</TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" onClick={() => handleDelete(s.id)}>
                        Delete
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

"use client";

import { useState } from "react";
import { Document, Page, Text, View, StyleSheet, pdf } from "@react-pdf/renderer";
import { saveAs } from "file-saver";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Download, FileJson, FileSpreadsheet, FileText } from "lucide-react";

type Holding = {
  symbol: string;
  name: string;
  sector: string;
  quantity: number;
  averageCost: number;
  currentPrice: number;
  totalCost: number;
  currentValue: number;
  unrealizedPL: number;
  unrealizedPLPercent: number;
};

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const pdfStyles = StyleSheet.create({
  page: { padding: 30, fontSize: 10 },
  title: { fontSize: 16, marginBottom: 10 },
  section: { marginTop: 12 },
  row: { flexDirection: "row", marginTop: 4 },
  cell: { flex: 1 },
  tableHeader: { flexDirection: "row", marginTop: 8, borderBottomWidth: 1, paddingBottom: 4 },
  tableRow: { flexDirection: "row", marginTop: 4 },
});

function PdfDocument({
  summary,
  holdings,
  generatedAt,
}: {
  summary: { totalValue: number; totalCost: number; totalUnrealizedPL: number; totalUnrealizedPLPercent: number; numberOfPositions: number };
  holdings: Array<{ symbol: string; name: string; quantity: number; averageCost: number; currentPrice: number; totalCost: number; currentValue: number; unrealizedPL: number; unrealizedPLPercent: number }>;
  generatedAt: string;
}) {
  return (
    <Document>
      <Page size="A4" style={pdfStyles.page}>
        <Text style={pdfStyles.title}>PSX Portfolio Report</Text>
        <Text>Generated: {generatedAt}</Text>
        <View style={pdfStyles.section}>
          <Text style={{ marginTop: 8 }}>Summary</Text>
          <Text>Total value: Rs {summary.totalValue.toLocaleString("en-PK")}</Text>
          <Text>Total cost: Rs {summary.totalCost.toLocaleString("en-PK")}</Text>
          <Text>Unrealized P&L: Rs {summary.totalUnrealizedPL.toLocaleString("en-PK")} ({summary.totalUnrealizedPLPercent >= 0 ? "+" : ""}{summary.totalUnrealizedPLPercent.toFixed(2)}%)</Text>
          <Text>Positions: {summary.numberOfPositions}</Text>
        </View>
        <View style={pdfStyles.section}>
          <Text style={{ marginTop: 12 }}>Holdings</Text>
          <View style={pdfStyles.tableHeader}>
            <Text style={[pdfStyles.cell, { flex: 0.8 }]}>Symbol</Text>
            <Text style={[pdfStyles.cell, { flex: 2 }]}>Name</Text>
            <Text style={[pdfStyles.cell, { flex: 0.6 }]}>Qty</Text>
            <Text style={[pdfStyles.cell, { flex: 1 }]}>Cost</Text>
            <Text style={[pdfStyles.cell, { flex: 1 }]}>Value</Text>
            <Text style={[pdfStyles.cell, { flex: 1 }]}>P&L %</Text>
          </View>
          {holdings.map((h) => (
            <View key={h.symbol} style={pdfStyles.tableRow}>
              <Text style={[pdfStyles.cell, { flex: 0.8 }]}>{h.symbol}</Text>
              <Text style={[pdfStyles.cell, { flex: 2 }]}>{h.name}</Text>
              <Text style={[pdfStyles.cell, { flex: 0.6 }]}>{h.quantity}</Text>
              <Text style={[pdfStyles.cell, { flex: 1 }]}>{h.totalCost.toFixed(0)}</Text>
              <Text style={[pdfStyles.cell, { flex: 1 }]}>{h.currentValue.toFixed(0)}</Text>
              <Text style={[pdfStyles.cell, { flex: 1 }]}>{h.unrealizedPLPercent >= 0 ? "+" : ""}{h.unrealizedPLPercent.toFixed(2)}%</Text>
            </View>
          ))}
        </View>
      </Page>
    </Document>
  );
}

export function PortfolioExportDropdown() {
  const [loading, setLoading] = useState<"csv" | "json" | "pdf" | null>(null);

  const fetchHoldings = async () => {
    const res = await fetch("/api/portfolio/holdings");
    const data = await res.json();
    if (!data.success) throw new Error("No data");
    return data.data;
  };

  const exportCsv = async () => {
    setLoading("csv");
    try {
      const { holdings } = await fetchHoldings();
      if (!holdings?.length) throw new Error("No holdings");
      const headers = ["Symbol", "Name", "Sector", "Qty", "Avg Cost", "Price", "Cost", "Value", "P&L", "P&L %"];
      const rows = (holdings as Holding[]).map((h) => [
        h.symbol,
        `"${(h.name ?? "").replace(/"/g, '""')}"`,
        h.sector,
        h.quantity,
        h.averageCost.toFixed(2),
        h.currentPrice.toFixed(2),
        h.totalCost.toFixed(2),
        h.currentValue.toFixed(2),
        h.unrealizedPL.toFixed(2),
        h.unrealizedPLPercent.toFixed(2),
      ].join(","));
      const csv = [headers.join(","), ...rows].join("\n");
      downloadBlob(new Blob([csv], { type: "text/csv" }), `portfolio-holdings-${new Date().toISOString().slice(0, 10)}.csv`);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  };

  const exportJson = async () => {
    setLoading("json");
    try {
      const data = await fetchHoldings();
      const json = JSON.stringify(data, null, 2);
      downloadBlob(new Blob([json], { type: "application/json" }), `portfolio-holdings-${new Date().toISOString().slice(0, 10)}.json`);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  };

  const downloadPdf = async () => {
    setLoading("pdf");
    try {
      const data = await fetchHoldings();
      if (!data?.holdings || !data?.summary) throw new Error("No data");
      const blob = await pdf(
        <PdfDocument
          summary={data.summary}
          holdings={data.holdings}
          generatedAt={new Date().toISOString()}
        />
      ).toBlob();
      saveAs(blob, `portfolio-report-${new Date().toISOString().slice(0, 10)}.pdf`);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(null);
    }
  };

  const busy = loading !== null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" disabled={busy} className="gap-1.5">
          <Download className="size-4" />
          {busy ? "Exporting…" : "Export"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        <DropdownMenuItem onClick={exportCsv} disabled={loading === "csv"}>
          <FileSpreadsheet className="size-4" />
          Export CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={exportJson} disabled={loading === "json"}>
          <FileJson className="size-4" />
          Export JSON
        </DropdownMenuItem>
        <DropdownMenuItem onClick={downloadPdf} disabled={loading === "pdf"}>
          <FileText className="size-4" />
          Download PDF report
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

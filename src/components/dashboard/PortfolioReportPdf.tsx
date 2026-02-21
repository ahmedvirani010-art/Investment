"use client";

import { useState } from "react";
import { Document, Page, Text, View, StyleSheet, pdf } from "@react-pdf/renderer";
import { saveAs } from "file-saver";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const styles = StyleSheet.create({
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
      <Page size="A4" style={styles.page}>
        <Text style={styles.title}>PSX Portfolio Report</Text>
        <Text>Generated: {generatedAt}</Text>
        <View style={styles.section}>
          <Text style={{ marginTop: 8 }}>Summary</Text>
          <Text>Total value: Rs {summary.totalValue.toLocaleString("en-PK")}</Text>
          <Text>Total cost: Rs {summary.totalCost.toLocaleString("en-PK")}</Text>
          <Text>Unrealized P&L: Rs {summary.totalUnrealizedPL.toLocaleString("en-PK")} ({summary.totalUnrealizedPLPercent >= 0 ? "+" : ""}{summary.totalUnrealizedPLPercent.toFixed(2)}%)</Text>
          <Text>Positions: {summary.numberOfPositions}</Text>
        </View>
        <View style={styles.section}>
          <Text style={{ marginTop: 12 }}>Holdings</Text>
          <View style={styles.tableHeader}>
            <Text style={[styles.cell, { flex: 0.8 }]}>Symbol</Text>
            <Text style={[styles.cell, { flex: 2 }]}>Name</Text>
            <Text style={[styles.cell, { flex: 0.6 }]}>Qty</Text>
            <Text style={[styles.cell, { flex: 1 }]}>Cost</Text>
            <Text style={[styles.cell, { flex: 1 }]}>Value</Text>
            <Text style={[styles.cell, { flex: 1 }]}>P&L %</Text>
          </View>
          {holdings.map((h) => (
            <View key={h.symbol} style={styles.tableRow}>
              <Text style={[styles.cell, { flex: 0.8 }]}>{h.symbol}</Text>
              <Text style={[styles.cell, { flex: 2 }]}>{h.name}</Text>
              <Text style={[styles.cell, { flex: 0.6 }]}>{h.quantity}</Text>
              <Text style={[styles.cell, { flex: 1 }]}>{h.totalCost.toFixed(0)}</Text>
              <Text style={[styles.cell, { flex: 1 }]}>{h.currentValue.toFixed(0)}</Text>
              <Text style={[styles.cell, { flex: 1 }]}>{h.unrealizedPLPercent >= 0 ? "+" : ""}{h.unrealizedPLPercent.toFixed(2)}%</Text>
            </View>
          ))}
        </View>
      </Page>
    </Document>
  );
}

export function PortfolioReportPdf() {
  const [loading, setLoading] = useState(false);

  const generatePdf = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/portfolio/holdings");
      const data = await res.json();
      if (!data.success || !data.data?.holdings || !data.data?.summary) throw new Error("No data");
      const blob = await pdf(
        <PdfDocument
          summary={data.data.summary}
          holdings={data.data.holdings}
          generatedAt={new Date().toISOString()}
        />
      ).toBlob();
      saveAs(blob, `portfolio-report-${new Date().toISOString().slice(0, 10)}.pdf`);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>PDF report</CardTitle>
        <p className="text-sm text-muted-foreground">
          Generate a PDF summary of your portfolio
        </p>
      </CardHeader>
      <CardContent>
        <Button variant="outline" size="sm" onClick={generatePdf} disabled={loading}>
          {loading ? "Generating..." : "Download PDF report"}
        </Button>
      </CardContent>
    </Card>
  );
}

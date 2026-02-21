import Link from "next/link";

const sections = [
  {
    title: "Portfolio",
    items: [
      { href: "/dashboard", label: "Overview", icon: "📊" },
      { href: "/dashboard/watchlist", label: "Watchlist", icon: "👁️" },
      { href: "/dashboard/performance", label: "Performance", icon: "📈" },
    ],
  },
  {
    title: "Trading",
    items: [
      { href: "/dashboard/plans", label: "Trade Plans", icon: "📋" },
      { href: "/dashboard/journal", label: "Journal", icon: "📓" },
      { href: "/dashboard/risk", label: "Risk", icon: "⚠️" },
    ],
  },
  {
    title: "Analysis",
    items: [
      { href: "/dashboard/liquidity", label: "Liquidity", icon: "💧" },
      { href: "/dashboard/fundamental", label: "Fundamental", icon: "📐" },
      { href: "/dashboard/technical", label: "Technical", icon: "📉" },
      { href: "/dashboard/hmm-regime", label: "HMM Regimes", icon: "🔀" },
      { href: "/dashboard/multivariate", label: "Multivariate BTC/GOLD", icon: "📊" },
      { href: "/dashboard/anomalies", label: "Anomalies", icon: "🔔" },
    ],
  },
  {
    title: "Data",
    items: [
      { href: "/dashboard/announcements", label: "Announcements", icon: "📢" },
      { href: "/dashboard/news", label: "News", icon: "📰" },
    ],
  },
  {
    title: "Setup",
    items: [
      { href: "/dashboard/setup", label: "Sectors & Scripts", icon: "⚙️" },
      { href: "/dashboard/settings", label: "Settings", icon: "🔑" },
    ],
  },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen bg-background">
      <aside className="w-52 border-r border-border bg-card flex flex-col shrink-0">
        <div className="p-4 border-b border-border">
          <Link href="/" className="font-semibold text-foreground hover:underline">
            PSX Investment
          </Link>
          <p className="text-xs text-muted-foreground mt-0.5">
            Portfolio & Risk
          </p>
        </div>
        <nav className="flex-1 overflow-y-auto p-2">
          {sections.map((section) => (
            <div key={section.title} className="mb-4">
              <p className="px-3 py-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                {section.title}
              </p>
              <div className="space-y-0.5">
                {section.items.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
                  >
                    <span className="shrink-0">{item.icon}</span>
                    <span className="truncate">{item.label}</span>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="p-2 border-t border-border shrink-0">
          <Link
            href="/llm"
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          >
            <span className="shrink-0">🤖</span>
            AI Assistant
          </Link>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}

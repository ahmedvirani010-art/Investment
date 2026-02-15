import Link from "next/link"
import { Activity, TrendingUp, Newspaper, BarChart3, Bell } from "lucide-react"

export default function Home() {
  const features = [
    {
      title: "Agent Dashboard",
      description: "Run and monitor investment analysis agents",
      icon: Activity,
      href: "/agents",
      color: "bg-blue-500"
    },
    {
      title: "Technical Analysis",
      description: "RSI, MACD, SMA and more indicators",
      icon: BarChart3,
      href: "/agents",
      color: "bg-green-500"
    },
    {
      title: "News Monitoring",
      description: "Track PSX news and sentiment analysis",
      icon: Newspaper,
      href: "/agents",
      color: "bg-purple-500"
    },
    {
      title: "Anomaly Detection",
      description: "Detect unusual trading patterns",
      icon: TrendingUp,
      href: "/agents",
      color: "bg-orange-500"
    }
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 to-zinc-100 dark:from-zinc-900 dark:to-black">
      <main className="container mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            PSX Investment Dashboard
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Automated analysis agents for Pakistan Stock Exchange
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {features.map((feature) => (
            <Link
              key={feature.title}
              href={feature.href}
              className="group relative overflow-hidden rounded-xl bg-white dark:bg-zinc-800 p-6 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1"
            >
              <div className={`${feature.color} w-12 h-12 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                <feature.icon className="h-6 w-6 text-white" />
              </div>
              <h3 className="text-lg font-semibold mb-2 text-gray-900 dark:text-white">
                {feature.title}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {feature.description}
              </p>
            </Link>
          ))}
        </div>

        <div className="text-center">
          <Link
            href="/agents"
            className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-medium px-8 py-4 rounded-full transition-colors shadow-lg hover:shadow-xl"
          >
            <Activity className="h-5 w-5" />
            Open Agent Dashboard
          </Link>
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
          <div>
            <div className="text-3xl font-bold text-blue-600 mb-2">4</div>
            <div className="text-gray-600 dark:text-gray-400">Active Agents</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-green-600 mb-2">30+</div>
            <div className="text-gray-600 dark:text-gray-400">PSX Stocks</div>
          </div>
          <div>
            <div className="text-3xl font-bold text-purple-600 mb-2">Real-time</div>
            <div className="text-gray-600 dark:text-gray-400">Analysis</div>
          </div>
        </div>
      </main>
    </div>
  )
}

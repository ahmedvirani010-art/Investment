'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PlayCircle, RefreshCw, Clock, CheckCircle, XCircle, Activity, ExternalLink } from 'lucide-react'

type Agent = {
  id: string
  name: string
  description: string
  type: string
  isActive: boolean
  config: string | null
  createdAt: string
  updatedAt: string
}

type AgentRun = {
  id: string
  agentId: string
  status: string
  startedAt: string
  completedAt: string | null
  duration: number | null
  parameters: string | null
  error: string | null
  agent: Agent
  results: any[]
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [loading, setLoading] = useState(true)
  const [runningAgents, setRunningAgents] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchAgents()
    fetchRuns()
    const interval = setInterval(fetchRuns, 5000) // Poll for updates every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchAgents = async () => {
    try {
      const res = await fetch('/api/agents')
      const data = await res.json()
      setAgents(data)
    } catch (error) {
      console.error('Error fetching agents:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchRuns = async () => {
    try {
      const res = await fetch('/api/agent-runs?limit=50')
      const data = await res.json()
      setRuns(data)

      // Update running agents
      const running = new Set<string>(
        data.filter((r: AgentRun) => r.status === 'running').map((r: AgentRun) => r.agentId)
      )
      setRunningAgents(running)
    } catch (error) {
      console.error('Error fetching runs:', error)
    }
  }

  const runAgent = async (agentId: string) => {
    try {
      setRunningAgents(prev => new Set(prev).add(agentId))

      const res = await fetch('/api/agent-runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agentId, parameters: {} })
      })

      if (!res.ok) throw new Error('Failed to run agent')

      fetchRuns()
    } catch (error) {
      console.error('Error running agent:', error)
      setRunningAgents(prev => {
        const next = new Set(prev)
        next.delete(agentId)
        return next
      })
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <RefreshCw className="h-4 w-4 animate-spin text-blue-500" />
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, any> = {
      running: 'default',
      completed: 'default',
      failed: 'destructive',
      pending: 'secondary'
    }

    return (
      <Badge variant={variants[status] || 'secondary'} className="capitalize">
        {status}
      </Badge>
    )
  }

  const formatDuration = (ms: number | null) => {
    if (!ms) return 'N/A'
    const seconds = Math.floor(ms / 1000)
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <RefreshCw className="h-8 w-8 animate-spin text-gray-500" />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">PSX Agent Dashboard</h1>
        <p className="text-gray-600">Manage and monitor investment analysis agents</p>
      </div>

      <Tabs defaultValue="agents" className="space-y-4">
        <TabsList>
          <TabsTrigger value="agents">
            <Activity className="h-4 w-4 mr-2" />
            Agents
          </TabsTrigger>
          <TabsTrigger value="runs">
            <Clock className="h-4 w-4 mr-2" />
            Run History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="agents" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agents.map(agent => (
              <Card key={agent.id} className="p-6">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold mb-2">{agent.name}</h3>
                    <p className="text-sm text-gray-600 mb-3">{agent.description}</p>
                    <div className="flex gap-2">
                      <Badge variant="outline">{agent.type}</Badge>
                      {agent.isActive ? (
                        <Badge variant="default">Active</Badge>
                      ) : (
                        <Badge variant="secondary">Inactive</Badge>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={() => runAgent(agent.id)}
                    disabled={!agent.isActive || runningAgents.has(agent.id)}
                    className="flex-1"
                  >
                    {runningAgents.has(agent.id) ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <PlayCircle className="h-4 w-4 mr-2" />
                        Run Agent
                      </>
                    )}
                  </Button>
                </div>

                {agent.config && (
                  <div className="mt-4 p-3 bg-gray-50 rounded text-xs">
                    <pre className="overflow-x-auto">
                      {JSON.stringify(JSON.parse(agent.config), null, 2)}
                    </pre>
                  </div>
                )}
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="runs" className="space-y-4">
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Completed</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Results</TableHead>
                  <TableHead>Error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {runs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-gray-500 py-8">
                      No agent runs yet. Run an agent to see results here.
                    </TableCell>
                  </TableRow>
                ) : (
                  runs.map(run => (
                    <TableRow key={run.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getStatusIcon(run.status)}
                          {getStatusBadge(run.status)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Link
                          href={`/agents/${run.id}`}
                          className="font-medium hover:text-blue-600 flex items-center gap-1"
                        >
                          {run.agent.name}
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {formatDate(run.startedAt)}
                      </TableCell>
                      <TableCell className="text-sm text-gray-600">
                        {run.completedAt ? formatDate(run.completedAt) : '-'}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDuration(run.duration)}
                      </TableCell>
                      <TableCell>
                        <Link href={`/agents/${run.id}`}>
                          <Badge variant="outline" className="cursor-pointer hover:bg-blue-50">
                            {run.results?.length || 0} results
                          </Badge>
                        </Link>
                      </TableCell>
                      <TableCell className="text-sm text-red-600 max-w-xs truncate">
                        {run.error || '-'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/table'
import { ArrowLeft, CheckCircle, XCircle, RefreshCw, Clock } from 'lucide-react'

type AgentRun = {
  id: string
  agentId: string
  status: string
  startedAt: string
  completedAt: string | null
  duration: number | null
  parameters: any
  error: string | null
  agent: {
    id: string
    name: string
    description: string
    type: string
  }
  results: Array<{
    id: string
    symbol: string | null
    data: any
    resultType: string
    severity: string | null
    createdAt: string
  }>
}

export default function AgentRunDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [run, setRun] = useState<AgentRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchRunDetails()
    const interval = setInterval(fetchRunDetails, 5000)
    return () => clearInterval(interval)
  }, [params.runId])

  const fetchRunDetails = async () => {
    try {
      const res = await fetch(`/api/agent-runs/${params.runId}`)
      if (!res.ok) {
        throw new Error('Failed to fetch run details')
      }
      const data = await res.json()
      setRun(data)
      setError(null)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <RefreshCw className="h-5 w-5 animate-spin text-blue-500" />
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <Clock className="h-5 w-5 text-gray-500" />
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

  const getSeverityBadge = (severity: string | null) => {
    if (!severity) return null

    const variants: Record<string, any> = {
      HIGH: 'destructive',
      MEDIUM: 'default',
      LOW: 'secondary'
    }

    return (
      <Badge variant={variants[severity] || 'secondary'}>
        {severity}
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

  if (error || !run) {
    return (
      <div className="container mx-auto py-8 px-4">
        <Button onClick={() => router.back()} variant="ghost" className="mb-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
        <Card className="p-8 text-center">
          <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">Error Loading Run</h2>
          <p className="text-gray-600">{error || 'Run not found'}</p>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <Button onClick={() => router.back()} variant="ghost" className="mb-4">
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Dashboard
      </Button>

      <div className="space-y-6">
        {/* Run Overview */}
        <Card className="p-6">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold mb-2">{run.agent.name}</h1>
              <p className="text-gray-600">{run.agent.description}</p>
            </div>
            <div className="flex items-center gap-2">
              {getStatusIcon(run.status)}
              {getStatusBadge(run.status)}
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-600 mb-1">Started</div>
              <div className="font-medium">{formatDate(run.startedAt)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Completed</div>
              <div className="font-medium">
                {run.completedAt ? formatDate(run.completedAt) : 'In progress...'}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Duration</div>
              <div className="font-medium">{formatDuration(run.duration)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600 mb-1">Results</div>
              <div className="font-medium">{run.results.length} items</div>
            </div>
          </div>

          {run.error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded">
              <div className="font-semibold text-red-900 mb-1">Error</div>
              <div className="text-sm text-red-700">{run.error}</div>
            </div>
          )}

          {run.parameters && Object.keys(run.parameters).length > 0 && (
            <div className="mt-4">
              <div className="text-sm font-semibold mb-2">Parameters</div>
              <pre className="p-3 bg-gray-50 rounded text-xs overflow-x-auto">
                {JSON.stringify(run.parameters, null, 2)}
              </pre>
            </div>
          )}
        </Card>

        {/* Results */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Results</h2>

          {run.results.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              {run.status === 'running' ? (
                <>
                  <RefreshCw className="h-12 w-12 animate-spin mx-auto mb-4 text-blue-500" />
                  <p>Agent is running. Results will appear here...</p>
                </>
              ) : (
                <>
                  <p>No results found for this run.</p>
                </>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Data</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {run.results.map(result => (
                  <TableRow key={result.id}>
                    <TableCell>
                      <Badge variant="outline">{result.resultType}</Badge>
                    </TableCell>
                    <TableCell className="font-medium">
                      {result.symbol || '-'}
                    </TableCell>
                    <TableCell>
                      {getSeverityBadge(result.severity)}
                    </TableCell>
                    <TableCell className="max-w-md">
                      <details className="cursor-pointer">
                        <summary className="text-sm text-blue-600 hover:underline">
                          View data
                        </summary>
                        <pre className="mt-2 p-2 bg-gray-50 rounded text-xs overflow-x-auto">
                          {JSON.stringify(result.data, null, 2)}
                        </pre>
                      </details>
                    </TableCell>
                    <TableCell className="text-sm text-gray-600">
                      {formatDate(result.createdAt)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>
      </div>
    </div>
  )
}

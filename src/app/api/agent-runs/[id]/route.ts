import { NextResponse } from 'next/server'
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

// GET /api/agent-runs/[id] - Get a specific agent run with results
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const run = await prisma.agentRun.findUnique({
      where: { id },
      include: {
        agent: true,
        results: {
          orderBy: { createdAt: 'desc' }
        }
      }
    })

    if (!run) {
      return NextResponse.json(
        { error: 'Agent run not found' },
        { status: 404 }
      )
    }

    // Parse JSON fields
    const parsedRun = {
      ...run,
      parameters: run.parameters ? JSON.parse(run.parameters) : null,
      results: run.results.map(r => ({
        ...r,
        data: JSON.parse(r.data)
      }))
    }

    return NextResponse.json(parsedRun)
  } catch (error) {
    console.error('Error fetching agent run:', error)
    return NextResponse.json(
      { error: 'Failed to fetch agent run' },
      { status: 500 }
    )
  }
}

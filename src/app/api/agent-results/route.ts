import { NextResponse } from 'next/server'
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

// GET /api/agent-results - Get agent results
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const runId = searchParams.get('runId')
    const symbol = searchParams.get('symbol')
    const resultType = searchParams.get('resultType')
    const severity = searchParams.get('severity')
    const limit = parseInt(searchParams.get('limit') || '100')

    const results = await prisma.agentResult.findMany({
      where: {
        ...(runId && { runId }),
        ...(symbol && { symbol }),
        ...(resultType && { resultType }),
        ...(severity && { severity })
      },
      include: {
        run: {
          include: {
            agent: true
          }
        }
      },
      orderBy: { createdAt: 'desc' },
      take: limit
    })

    // Parse JSON data field
    const parsedResults = results.map(r => ({
      ...r,
      data: JSON.parse(r.data)
    }))

    return NextResponse.json(parsedResults)
  } catch (error) {
    console.error('Error fetching agent results:', error)
    return NextResponse.json(
      { error: 'Failed to fetch agent results' },
      { status: 500 }
    )
  }
}

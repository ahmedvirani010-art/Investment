import { NextResponse } from 'next/server'
import { PrismaClient } from '@prisma/client'
import { spawn } from 'child_process'
import path from 'path'

const prisma = new PrismaClient()

// GET /api/agent-runs - Get all agent runs
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const agentId = searchParams.get('agentId')
    const status = searchParams.get('status')
    const limit = parseInt(searchParams.get('limit') || '50')

    const runs = await prisma.agentRun.findMany({
      where: {
        ...(agentId && { agentId }),
        ...(status && { status })
      },
      include: {
        agent: true,
        results: {
          select: {
            id: true,
            symbol: true,
            resultType: true,
            severity: true,
            createdAt: true
          }
        }
      },
      orderBy: { startedAt: 'desc' },
      take: limit
    })

    return NextResponse.json(runs)
  } catch (error) {
    console.error('Error fetching agent runs:', error)
    return NextResponse.json(
      { error: 'Failed to fetch agent runs' },
      { status: 500 }
    )
  }
}

// POST /api/agent-runs - Run an agent
export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { agentId, parameters } = body

    // Get agent details
    const agent = await prisma.agent.findUnique({
      where: { id: agentId }
    })

    if (!agent) {
      return NextResponse.json(
        { error: 'Agent not found' },
        { status: 404 }
      )
    }

    if (!agent.isActive) {
      return NextResponse.json(
        { error: 'Agent is not active' },
        { status: 400 }
      )
    }

    // Create agent run record
    const run = await prisma.agentRun.create({
      data: {
        agentId,
        status: 'running',
        parameters: parameters ? JSON.stringify(parameters) : null
      }
    })

    // Run the agent asynchronously
    executeAgent(agent, run.id, parameters).catch(console.error)

    return NextResponse.json(run, { status: 201 })
  } catch (error) {
    console.error('Error creating agent run:', error)
    return NextResponse.json(
      { error: 'Failed to create agent run' },
      { status: 500 }
    )
  }
}

// Execute the Python agent
async function executeAgent(agent: any, runId: string, parameters: any) {
  const startTime = Date.now()

  try {
    // Map agent type to Python script
    const scriptMap: Record<string, string> = {
      'anomaly': 'psx_anomaly_agent.py',
      'news': 'psx_news_agent.py',
      'technical': 'psx_technical_agent.py',
      'announcement': 'psx_announcement_scraper.py'
    }

    const scriptName = scriptMap[agent.type]
    if (!scriptName) {
      throw new Error(`Unknown agent type: ${agent.type}`)
    }

    const scriptPath = path.join(process.cwd(), scriptName)

    // Execute Python script
    const pythonProcess = spawn('python3', [scriptPath])

    let outputData = ''
    let errorData = ''

    pythonProcess.stdout.on('data', (data) => {
      outputData += data.toString()
    })

    pythonProcess.stderr.on('data', (data) => {
      errorData += data.toString()
    })

    pythonProcess.on('close', async (code) => {
      const duration = Date.now() - startTime

      if (code === 0) {
        // Parse output and store results
        try {
          const results = parseAgentOutput(agent.type, outputData)

          // Store results in database
          for (const result of results) {
            await prisma.agentResult.create({
              data: {
                runId,
                symbol: result.symbol,
                data: JSON.stringify(result.data),
                resultType: result.type,
                severity: result.severity
              }
            })
          }

          // Update run status
          await prisma.agentRun.update({
            where: { id: runId },
            data: {
              status: 'completed',
              completedAt: new Date(),
              duration
            }
          })
        } catch (parseError) {
          console.error('Error parsing agent output:', parseError)
          await prisma.agentRun.update({
            where: { id: runId },
            data: {
              status: 'failed',
              completedAt: new Date(),
              duration,
              error: `Failed to parse output: ${parseError}`
            }
          })
        }
      } else {
        await prisma.agentRun.update({
          where: { id: runId },
          data: {
            status: 'failed',
            completedAt: new Date(),
            duration,
            error: errorData || `Process exited with code ${code}`
          }
        })
      }
    })
  } catch (error: any) {
    const duration = Date.now() - startTime
    await prisma.agentRun.update({
      where: { id: runId },
      data: {
        status: 'failed',
        completedAt: new Date(),
        duration,
        error: error.message
      }
    })
  }
}

// Parse agent output based on agent type
function parseAgentOutput(agentType: string, output: string): any[] {
  const results: any[] = []

  // For now, return a placeholder
  // In a real implementation, you would parse the actual Python output
  // or use a JSON output format from the Python scripts

  return results
}

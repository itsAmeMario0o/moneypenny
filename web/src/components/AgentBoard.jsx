// The TradingAgents team as a board: one column per stage, one card per agent.
// Each agent is "waiting", "working" or "done", worked out from the run's events.

const STAGES = ['Analysts', 'Research debate', 'Trader', 'Risk debate', 'Decision']
const ANALYST_KEYS = ['market', 'social', 'news', 'fundamentals']

// Leave out analysts that were not selected for this run.
function agentsInRun(agents, run) {
  const result = []
  for (const agent of agents) {
    const isAnalyst = ANALYST_KEYS.includes(agent.key)
    if (isAnalyst && !run.settings.analysts.includes(agent.key)) {
      continue
    }
    result.push(agent)
  }
  return result
}

function countEvents(run, agentKey) {
  let count = 0
  for (const event of run.events) {
    if (event.agent === agentKey) {
      count = count + 1
    }
  }
  return count
}

// The stage being worked on now: the first one with an agent that hasn't spoken yet.
function findActiveStage(agents, run) {
  if (run.status !== 'running') {
    return null
  }
  for (const stage of STAGES) {
    for (const agent of agents) {
      if (agent.stage === stage && countEvents(run, agent.key) === 0) {
        return stage
      }
    }
  }
  return null
}

function statusOf(agent, run, activeStage) {
  if (countEvents(run, agent.key) > 0) {
    return 'done'
  }
  if (agent.stage === activeStage) {
    return 'working'
  }
  return 'waiting'
}

export default function AgentBoard({ agents, run }) {
  const team = agentsInRun(agents, run)
  const activeStage = findActiveStage(team, run)

  return (
    <div className="board">
      {STAGES.map((stage) => (
        <div key={stage} className={stage === activeStage ? 'board-stage active' : 'board-stage'}>
          <div className="stat-label">{stage}</div>
          {team.filter((agent) => agent.stage === stage).map((agent) => {
            const status = statusOf(agent, run, activeStage)
            const messages = countEvents(run, agent.key)
            return (
              <div key={agent.key} className={'agent ' + status}>
                <span className="agent-dot" aria-hidden="true" />
                <div>
                  <div className="agent-name">{agent.name}</div>
                  <div className="small dim">
                    {status === 'done' ? messages + (messages === 1 ? ' message' : ' messages') : status}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ))}
    </div>
  )
}

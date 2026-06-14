import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Brain, Zap, Inbox, MessageSquare, Activity, Terminal, Send, Check, X, Plus, DollarSign, TrendingUp, Shield, Key, Users, ExternalLink, Copy, Clock, Star, Award, UserPlus, AlertCircle, Eye, Heart, Server, Cpu, Database, RefreshCw, AlertTriangle, Layers, CircleDot, HeartHandshake, Sparkles, Target, Waves, Radio
} from 'lucide-react'

// --- CONFIG ---
const API_URL = '/api'
const WS_URL = 'ws://localhost:3000/ws'

function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [overview, setOverview] = useState(null)
  const [stats, setStats] = useState({ intents: 0, claims: 0 })
  const [connected, setConnected] = useState(false)
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [chatMessages, setChatMessages] = useState([])
  const [inboxItems, setInboxItems] = useState([])
  const [boardData, setBoardData] = useState({ intent: [], building: [], deployed: [] })
  const [treasuryData, setTreasuryData] = useState(null)
  const [missionStats, setMissionStats] = useState({ active_tokens: 0, pending_tasks: 0, completed_tasks: 0, blocked_services: 0 })
  const [missionTokens, setMissionTokens] = useState([])
  const [missionTasks, setMissionTasks] = useState([])
  const [teamStats, setTeamStats] = useState({ total_humans: 0, active_humans: 0, working_now: 0, active_tokens: 0 })
  const [teamHumans, setTeamHumans] = useState([])
  const [teamActivity, setTeamActivity] = useState([])
  const [teamRecommendations, setTeamRecommendations] = useState([])
  const [systemIntelligence, setSystemIntelligence] = useState(null)
  const [commonsData, setCommonsData] = useState(null)
  const [sparketData, setSparketData] = useState(null)
  const [dataSystem, setDataSystem] = useState(null)
  const [ariaToken, setAriaToken] = useState(() => localStorage.getItem('aria_admin_token') || '')
  
  const ws = useRef(null)

  useEffect(() => {
    fetch(`${API_URL}/overview`).then(res => res.json()).then(setOverview).catch(() => {})
    fetch(`${API_URL}/chat`).then(res => res.json()).then(setChatMessages)
    fetch(`${API_URL}/graph`).then(res => res.json()).then(setGraphData)
    fetch(`${API_URL}/inbox`).then(res => res.json()).then(setInboxItems)
    fetch(`${API_URL}/board`).then(res => res.json()).then(setBoardData)
    fetch(`${API_URL}/treasury`).then(res => res.json()).then(setTreasuryData)
    fetch(`${API_URL}/mission-control/stats`).then(res => res.json()).then(setMissionStats)
    fetch(`${API_URL}/mission-control/tokens`).then(res => res.json()).then(setMissionTokens)
    fetch(`${API_URL}/mission-control/tasks`).then(res => res.json()).then(setMissionTasks)
    // Team Hub data
    fetch(`${API_URL}/team/stats`).then(res => res.json()).then(setTeamStats).catch(() => {})
    fetch(`${API_URL}/team/humans`).then(res => res.json()).then(setTeamHumans).catch(() => {})
    fetch(`${API_URL}/team/activity?limit=20`).then(res => res.json()).then(setTeamActivity).catch(() => {})
    fetch(`${API_URL}/team/recommendations`).then(res => res.json()).then(setTeamRecommendations).catch(() => {})
    // System Intelligence data
    fetch(`${API_URL}/system-intelligence`).then(res => res.json()).then(setSystemIntelligence).catch(() => {})
    // Commons Ministry data (Trust Index)
    fetch(`${API_URL}/commons`).then(res => res.json()).then(setCommonsData).catch(() => {})
    // SPARKET data
    fetch(`${API_URL}/sparket`).then(res => res.json()).then(setSparketData).catch(() => {})
    // Data System (Nerve Center flywheel)
    fetch(`${API_URL}/data-system/status`).then(res => res.json()).then(setDataSystem).catch(() => {})
    // Refresh intelligence and commons every 30 seconds
    const intelInterval = setInterval(() => {
      fetch(`${API_URL}/overview`).then(res => res.json()).then(setOverview).catch(() => {})
      fetch(`${API_URL}/system-intelligence`).then(res => res.json()).then(setSystemIntelligence).catch(() => {})
      fetch(`${API_URL}/commons`).then(res => res.json()).then(setCommonsData).catch(() => {})
      fetch(`${API_URL}/sparket`).then(res => res.json()).then(setSparketData).catch(() => {})
      fetch(`${API_URL}/data-system/status`).then(res => res.json()).then(setDataSystem).catch(() => {})
    }, 30000)
    return () => clearInterval(intelInterval)
  }, [])

  useEffect(() => {
    const connect = () => {
      ws.current = new WebSocket(WS_URL)
      ws.current.onopen = () => setConnected(true)
      ws.current.onclose = () => { setConnected(false); setTimeout(connect, 3000) }
      ws.current.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'stats_update') setStats(msg.data)
        if (msg.type === 'graph_update') setGraphData(msg.data)
        if (msg.type === 'chat_new') setChatMessages(prev => [...prev, msg.data])
        if (msg.type === 'board_update') setBoardData(msg.data)
        if (msg.type === 'treasury_update') setTreasuryData(msg.data)
        if (msg.type === 'tokens_update') setMissionTokens(msg.data)
        if (msg.type === 'tasks_update') setMissionTasks(msg.data)
        if (msg.type === 'team_update') setTeamHumans(msg.data)
      }
    }
    connect()
    return () => ws.current?.close()
  }, [])

  const sendMessage = async (text) => {
    await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: text, sender: "ARCHITECT" })
    })
  }

  const createMission = async (name, desc) => {
    await fetch(`${API_URL}/mission`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, desc })
    })
  }

  return (
    <div className="flex h-screen bg-god-bg text-white font-mono overflow-hidden">
      <nav className="w-20 border-r border-white/10 flex flex-col items-center py-6 space-y-8 z-50 glass">
        <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(147,51,234,0.5)]">
          <Terminal size={20} />
        </div>
        <div className="flex-1 flex flex-col space-y-4 w-full">
          <NavIcon icon={Target} label="Overview" active={activeTab === 'overview'} onClick={() => setActiveTab('overview')} />
          {showAdvanced && (
            <>
              <NavIcon icon={Brain} label="Brain" active={activeTab === 'brain'} onClick={() => setActiveTab('brain')} />
              <NavIcon icon={Zap} label="Muscle" active={activeTab === 'muscle'} onClick={() => setActiveTab('muscle')} />
              <NavIcon icon={DollarSign} label="Treasury" active={activeTab === 'treasury'} onClick={() => setActiveTab('treasury')} />
              <NavIcon icon={HeartHandshake} label="Commons" active={activeTab === 'commons'} onClick={() => setActiveTab('commons')} />
              <NavIcon icon={Key} label="Mission" active={activeTab === 'mission'} onClick={() => setActiveTab('mission')} badge={missionStats.pending_tasks} />
              <NavIcon icon={Users} label="Team" active={activeTab === 'team'} onClick={() => setActiveTab('team')} badge={teamStats.working_now} />
              <NavIcon icon={Eye} label="Intel" active={activeTab === 'intel'} onClick={() => setActiveTab('intel')} badge={systemIntelligence?.notifications?.filter(n => !n.read).length || 0} />
              <NavIcon icon={Database} label="Data" active={activeTab === 'data'} onClick={() => setActiveTab('data')} />
              <NavIcon icon={Radio} label="Aria" active={activeTab === 'aria'} onClick={() => setActiveTab('aria')} />
              <NavIcon icon={Sparkles} label="Sparket" active={activeTab === 'sparket'} onClick={() => setActiveTab('sparket')} />
              <NavIcon icon={Inbox} label="Inbox" active={activeTab === 'inbox'} onClick={() => setActiveTab('inbox')} />
              <NavIcon icon={MessageSquare} label="Chat" active={activeTab === 'chat'} onClick={() => setActiveTab('chat')} />
            </>
          )}
          <NavIcon
            icon={Layers}
            label={showAdvanced ? "Simple" : "Advanced"}
            active={false}
            onClick={() => { setShowAdvanced(v => !v); setActiveTab('overview') }}
          />
        </div>
        <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500 shadow-[0_0_10px_#22c55e]' : 'bg-red-500 animate-pulse'}`} />
      </nav>

      <main className="flex-1 flex flex-col relative">
        <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 glass z-40">
          <h1 className="text-xl font-bold tracking-[0.2em] text-purple-400">GOD MODE // THE COUNCIL</h1>
          <div className="flex gap-6 text-xs text-gray-400">
            {treasuryData && <Stat label="TVL" value={`$${treasuryData.tvl.toLocaleString()}`} color="text-yellow-400" />}
            <Stat label="ACTIVE INTENTS" value={stats.intents} />
            <Stat label="ACTIVE CLAIMS" value={stats.claims} />
          </div>
        </header>

        <div className="flex-1 p-8 overflow-y-auto relative bg-grid-pattern">
          <AnimatePresence mode="wait">
            <motion.div key={activeTab} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="h-full">
              {activeTab === 'overview' && <OverviewView overview={overview} />}
              {activeTab === 'brain' && <BrainView board={boardData} onCreate={createMission} />}
              {activeTab === 'muscle' && <SystemGraph data={graphData} />}
              {activeTab === 'treasury' && <TreasuryView data={treasuryData} />}
              {activeTab === 'commons' && <CommonsView data={commonsData} onRefresh={() => fetch(`${API_URL}/commons`).then(res => res.json()).then(setCommonsData)} />}
              {activeTab === 'mission' && <MissionControlView stats={missionStats} tokens={missionTokens} tasks={missionTasks} />}
              {activeTab === 'team' && <TeamHubView stats={teamStats} humans={teamHumans} activity={teamActivity} recommendations={teamRecommendations} tokens={missionTokens} />}
              {activeTab === 'intel' && <SystemIntelligenceView data={systemIntelligence} onRefresh={() => fetch(`${API_URL}/system-intelligence`).then(res => res.json()).then(setSystemIntelligence)} />}
              {activeTab === 'data' && <DataSystemView data={dataSystem} onRefresh={() => fetch(`${API_URL}/data-system/status`).then(res => res.json()).then(setDataSystem)} onRunDigest={async (body) => { const res = await fetch(`${API_URL}/data-system/digest/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); return await res.json() }} onRecordOutcome={async (body) => { const res = await fetch(`${API_URL}/data-system/outcomes/record`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); return await res.json() }} />}
              {activeTab === 'aria' && <AriaControlView ariaToken={ariaToken} setAriaToken={setAriaToken} />}
              {activeTab === 'sparket' && <SparketView data={sparketData} onRefresh={() => fetch(`${API_URL}/sparket`).then(res => res.json()).then(setSparketData)} />}
              {activeTab === 'inbox' && <InboxView items={inboxItems} />}
              {activeTab === 'chat' && <ChatView messages={chatMessages} onSend={sendMessage} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}

function NavIcon({ icon: Icon, label, active, onClick, badge }) {
  return (
    <button onClick={onClick} className={`w-full h-14 flex flex-col items-center justify-center transition-all relative ${active ? 'border-l-2 border-purple-500 bg-white/5 text-purple-400' : 'text-gray-500 hover:text-gray-300'}`}>
      <Icon size={24} /> <span className="text-[10px] mt-1">{label}</span>
      {badge > 0 && <span className="absolute top-2 right-2 bg-red-500 text-white text-[9px] px-1.5 py-0.5 rounded-full">{badge}</span>}
    </button>
  )
}

function Stat({ label, value, color = "text-white" }) {
  return (
    <div className="flex flex-col items-end">
      <span className="text-[10px] opacity-50">{label}</span>
      <span className={`font-bold ${color}`}>{value}</span>
    </div>
  )
}

function OverviewView({ overview }) {
  if (!overview) {
    return (
      <div className="flex flex-col justify-center items-center h-full text-gray-500">
        <Target size={48} className="mb-4 opacity-30" />
        <p>Loading Overview...</p>
        <p className="text-xs mt-2">Money • Health • Do Now</p>
      </div>
    )
  }
  
  const treasury = overview?.money?.treasury
  const trading = overview?.money?.trading_stats
  const autoHealerHealth = overview?.health?.auto_healer?.health
  const topTask = overview?.do_now?.top_task
  const consciousnessVerifier = overview?.experimental?.consciousness_verifier
  
  const tvl = Number(treasury?.tvl ?? 0)
  const cash = Number(treasury?.cash ?? 0)
  const pnl24h = Number(treasury?.pnl_24h ?? 0)
  const trades = trading?.total_trades
  const totalPnl = trading?.total_pnl
  
  const healthScore = autoHealerHealth?.health_score
  const healthy = autoHealerHealth?.healthy
  const total = autoHealerHealth?.total_services
  
  const doNowTitle = topTask ? (topTask.api_name || topTask.capability || topTask.title || "Next Task") : "No pending tasks"
  const doNowSub = topTask
    ? `${topTask.service || "unknown"} • ${topTask.estimated_time || "unknown time"}`
    : "System has no pending work items."
  
  return (
    <div className="h-full flex flex-col space-y-6">
      <div className="grid grid-cols-3 gap-6">
        <Card
          title="MONEY"
          value={`$${tvl.toLocaleString()}`}
          icon={DollarSign}
          color="text-yellow-400"
          sub={`Cash $${cash.toLocaleString()} • 24h PnL ${pnl24h >= 0 ? "+" : ""}${pnl24h} • Trades ${trades ?? "—"} • Total PnL ${totalPnl ?? "—"}`}
        />
        <Card
          title="HEALTH"
          value={typeof healthScore === "number" ? `${healthScore.toFixed(0)}%` : "—"}
          icon={Shield}
          color={typeof healthScore === "number" && healthScore >= 95 ? "text-green-400" : "text-yellow-400"}
          sub={typeof healthy === "number" && typeof total === "number" ? `${healthy}/${total} services healthy (Auto-Healer)` : "Auto-Healer data unavailable"}
        />
        <Card
          title="DO NOW"
          value={doNowTitle}
          icon={Zap}
          color="text-purple-400"
          sub={doNowSub}
        />
      </div>
      
      <div className="glass rounded-xl p-6 border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-gray-300 tracking-wider">ADVANCED / EXPERIMENTAL</h3>
          <span className="text-[10px] text-gray-500">Truth over theater</span>
        </div>
        <div className="grid grid-cols-3 gap-6">
          <div className="bg-black/20 rounded-lg p-4 border border-white/10">
            <div className="text-xs text-gray-400 mb-2">Consciousness (Verifier)</div>
            <div className="text-lg font-bold text-blue-400">{consciousnessVerifier?.status || "unreachable"}</div>
            <div className="text-xs text-gray-500 mt-1">Secondary service • metrics-only</div>
          </div>
          <div className="bg-black/20 rounded-lg p-4 border border-white/10">
            <div className="text-xs text-gray-400 mb-2">Last Update</div>
            <div className="text-sm font-bold">{overview?.timestamp || "—"}</div>
            <div className="text-xs text-gray-500 mt-1">Overview refreshes every 30s</div>
          </div>
          <div className="bg-black/20 rounded-lg p-4 border border-white/10">
            <div className="text-xs text-gray-400 mb-2">Mode</div>
            <div className="text-lg font-bold text-green-400">Simple</div>
            <div className="text-xs text-gray-500 mt-1">Use left nav to toggle Advanced</div>
          </div>
        </div>
      </div>
    </div>
  )
}

// --- DATA SYSTEM VIEW (How the flywheel works + how to operate it) ---
function DataSystemView({ data, onRefresh, onRunDigest, onRecordOutcome }) {
  const [digestMode, setDigestMode] = useState("both")
  const [maxIntents, setMaxIntents] = useState(3)
  const [ttlHours, setTtlHours] = useState(24)
  const [running, setRunning] = useState(false)
  const [runResult, setRunResult] = useState(null)

  const [outcomeCategory, setOutcomeCategory] = useState("leadgen")
  const [outcomeActionTitle, setOutcomeActionTitle] = useState("")
  const [outcomeOutcome, setOutcomeOutcome] = useState("positive")
  const [metricName, setMetricName] = useState("")
  const [metricValue, setMetricValue] = useState("")
  const [outcomeNotes, setOutcomeNotes] = useState("")
  const [recording, setRecording] = useState(false)
  const [recordResult, setRecordResult] = useState(null)

  if (!data) {
    return (
      <div className="flex justify-center items-center h-full text-gray-500">
        <div className="text-center">
          <RefreshCw className="animate-spin mx-auto mb-4" size={32} />
          <div>Loading Data System...</div>
          <div className="text-xs mt-2">Pipeline • Digest • Intents • Outcomes</div>
        </div>
      </div>
    )
  }

  const cfg = data.config || {}
  const pipeline = data.pipeline || {}
  const intents = data.intents_recent?.intents || []
  const outcomes = data.outcomes_recent?.outcomes || []
  const outcomeStats = data.outcomes_stats || {}

  const pipelineStatus = pipeline.status || "unknown"
  const statusColor = pipelineStatus === "green" ? "text-green-400" : pipelineStatus === "yellow" ? "text-yellow-400" : "text-red-400"

  const sources = pipeline.sources?.freshness || {}
  const staleSources = Object.entries(sources).filter(([, v]) => v && v.fresh === false)

  const runDigest = async () => {
    setRunning(true)
    setRunResult(null)
    try {
      const body = {
        hours: 24,
        min_relevance: 0.6,
        limit: 80,
        mode: digestMode,
        push_to_strategic: true,
        create_intents: true,
        max_intents: Number(maxIntents),
        intent_ttl_hours: Number(ttlHours),
        dry_run: false
      }
      const res = await onRunDigest(body)
      setRunResult(res)
      onRefresh?.()
    } catch (e) {
      setRunResult({ error: String(e) })
    } finally {
      setRunning(false)
    }
  }

  const recordOutcome = async () => {
    setRecording(true)
    setRecordResult(null)
    try {
      const mv = metricValue === "" ? null : Number(metricValue)
      const body = {
        category: outcomeCategory,
        action_title: outcomeActionTitle,
        outcome: outcomeOutcome,
        metric_name: metricName || null,
        metric_value: Number.isFinite(mv) ? mv : null,
        notes: outcomeNotes || null,
        related_urls: [],
        push_to_mem0: true,
        push_to_strategic: true
      }
      const res = await onRecordOutcome(body)
      setRecordResult(res)
      onRefresh?.()
    } catch (e) {
      setRecordResult({ error: String(e) })
    } finally {
      setRecording(false)
    }
  }

  return (
    <div className="h-full flex flex-col space-y-6 overflow-y-auto">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold flex items-center gap-3">
          <Database className="text-blue-400" /> DATA SYSTEM
        </h2>
        <button onClick={onRefresh} className="bg-blue-600/20 hover:bg-blue-600/40 text-blue-300 px-4 py-2 rounded flex items-center gap-2 text-sm">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Quick Map */}
      <div className="glass rounded-xl p-6">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-blue-300 flex items-center gap-2"><Waves size={16}/> THE FLYWHEEL</h3>
          <div className="text-xs text-gray-500">Doc: <span className="text-gray-300">{cfg.doc_path || "docs/coordination/DATA_SYSTEM_MAP.md"}</span></div>
        </div>
        <div className="mt-4 grid grid-cols-7 gap-3 text-xs">
          <div className="bg-white/5 rounded-lg p-3 border border-white/10">
            <div className="text-gray-400">SOURCES</div>
            <div className="font-bold">HN • arXiv • RSS • CoinGlass</div>
          </div>
          <div className="flex items-center justify-center text-gray-500">→</div>
          <div className="bg-white/5 rounded-lg p-3 border border-white/10">
            <div className="text-gray-400">DATA SERVICE</div>
            <div className="font-bold">/api/data/*</div>
            <div className="text-gray-500">{cfg.data_service_url}</div>
          </div>
          <div className="flex items-center justify-center text-gray-500">→</div>
          <div className="bg-white/5 rounded-lg p-3 border border-white/10">
            <div className="text-gray-400">NERVE CENTER</div>
            <div className="font-bold">Digest • Intents • Outcomes</div>
            <div className="text-gray-500">{cfg.nerve_center_url}</div>
          </div>
          <div className="flex items-center justify-center text-gray-500">→</div>
          <div className="bg-white/5 rounded-lg p-3 border border-white/10">
            <div className="text-gray-400">STRATEGIC INTEL</div>
            <div className="font-bold">/api/v1/signals</div>
            <div className="text-gray-500">{cfg.strategic_intel_url}</div>
          </div>
        </div>
        <div className="mt-3 text-xs text-gray-500">
          Outcome loop: execute → <span className="text-gray-300">POST /api/outcomes/record</span> → learns via Mem0 + informs Strategic Intel.
        </div>
      </div>

      {/* Pipeline health */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass p-4 rounded-xl border-l-4 border-blue-500">
          <div className="text-xs text-gray-400 mb-1">PIPELINE</div>
          <div className={`text-2xl font-bold ${statusColor}`}>{String(pipelineStatus).toUpperCase()}</div>
          <div className="text-xs text-gray-500">Freshness + dependencies</div>
        </div>
        <div className="glass p-4 rounded-xl border-l-4 border-yellow-500">
          <div className="text-xs text-gray-400 mb-1">STALE SOURCES</div>
          <div className="text-2xl font-bold text-yellow-400">{staleSources.length}</div>
          <div className="text-xs text-gray-500">{staleSources.slice(0, 2).map(([k]) => k).join(", ") || "None"}</div>
        </div>
        <div className="glass p-4 rounded-xl border-l-4 border-green-500">
          <div className="text-xs text-gray-400 mb-1">OUTCOMES (7D)</div>
          <div className="text-2xl font-bold text-green-400">{outcomeStats.total || 0}</div>
          <div className="text-xs text-gray-500">Positive: {outcomeStats.by_outcome?.positive || 0} • Negative: {outcomeStats.by_outcome?.negative || 0}</div>
        </div>
      </div>

      {/* Actions */}
      <div className="grid grid-cols-2 gap-6">
        <div className="glass rounded-xl p-6">
          <h3 className="font-bold text-blue-300 flex items-center gap-2 mb-4"><Radio size={16}/> RUN ACTION DIGEST</h3>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>
              <div className="text-xs text-gray-500 mb-1">MODE</div>
              <select value={digestMode} onChange={e => setDigestMode(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded px-2 py-2">
                <option value="both">both</option>
                <option value="trading">trading</option>
                <option value="leadgen">leadgen</option>
              </select>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">MAX INTENTS</div>
              <input value={maxIntents} onChange={e => setMaxIntents(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded px-2 py-2" />
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">TTL (HOURS)</div>
              <input value={ttlHours} onChange={e => setTtlHours(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded px-2 py-2" />
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button disabled={running} onClick={runDigest} className="bg-blue-600/30 hover:bg-blue-600/50 disabled:opacity-50 text-blue-200 px-4 py-2 rounded flex items-center gap-2 text-sm">
              <Zap size={14} /> {running ? "Running..." : "Run Digest + Create Intents"}
            </button>
            <button onClick={onRefresh} className="bg-white/5 hover:bg-white/10 text-gray-300 px-4 py-2 rounded text-sm">Reload</button>
          </div>
          {runResult && (
            <div className="mt-4 text-xs bg-black/40 border border-white/10 rounded p-3 text-gray-300">
              <div className="text-gray-500 mb-2">LAST RUN RESULT</div>
              <pre className="whitespace-pre-wrap break-words">{JSON.stringify(runResult, null, 2)}</pre>
            </div>
          )}
        </div>

        <div className="glass rounded-xl p-6">
          <h3 className="font-bold text-green-300 flex items-center gap-2 mb-4"><Check size={16}/> RECORD OUTCOME</h3>
          <div className="grid grid-cols-3 gap-3 text-sm">
            <div>
              <div className="text-xs text-gray-500 mb-1">CATEGORY</div>
              <select value={outcomeCategory} onChange={e => setOutcomeCategory(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded px-2 py-2">
                <option value="trading">trading</option>
                <option value="leadgen">leadgen</option>
                <option value="system">system</option>
                <option value="other">other</option>
              </select>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">OUTCOME</div>
              <select value={outcomeOutcome} onChange={e => setOutcomeOutcome(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded px-2 py-2">
                <option value="positive">positive</option>
                <option value="neutral">neutral</option>
                <option value="negative">negative</option>
              </select>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">METRIC VALUE</div>
              <input value={metricValue} onChange={e => setMetricValue(e.target.value)} placeholder="e.g. 1, 25.3" className="w-full bg-black/40 border border-white/10 rounded px-2 py-2" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm mt-3">
            <div>
              <div className="text-xs text-gray-500 mb-1">ACTION TITLE</div>
              <input value={outcomeActionTitle} onChange={e => setOutcomeActionTitle(e.target.value)} placeholder="Paste a digest action title" className="w-full bg-black/40 border border-white/10 rounded px-2 py-2" />
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-1">METRIC NAME</div>
              <input value={metricName} onChange={e => setMetricName(e.target.value)} placeholder="pnl_usd | leads_booked | uc_revenue" className="w-full bg-black/40 border border-white/10 rounded px-2 py-2" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-xs text-gray-500 mb-1">NOTES</div>
            <textarea value={outcomeNotes} onChange={e => setOutcomeNotes(e.target.value)} rows={3} className="w-full bg-black/40 border border-white/10 rounded px-2 py-2" placeholder="What happened? What’s the lesson?" />
          </div>
          <div className="mt-4 flex gap-3">
            <button disabled={recording || !outcomeActionTitle} onClick={recordOutcome} className="bg-green-600/30 hover:bg-green-600/50 disabled:opacity-50 text-green-200 px-4 py-2 rounded flex items-center gap-2 text-sm">
              <Send size={14} /> {recording ? "Recording..." : "Record Outcome"}
            </button>
          </div>
          {recordResult && (
            <div className="mt-4 text-xs bg-black/40 border border-white/10 rounded p-3 text-gray-300">
              <div className="text-gray-500 mb-2">RECORD RESULT</div>
              <pre className="whitespace-pre-wrap break-words">{JSON.stringify(recordResult, null, 2)}</pre>
            </div>
          )}
        </div>
      </div>

      {/* Intents + Outcomes */}
      <div className="grid grid-cols-2 gap-6">
        <div className="glass rounded-xl p-6">
          <h3 className="font-bold text-purple-300 flex items-center gap-2 mb-4"><Layers size={16}/> RECENT INTENTS</h3>
          <div className="text-xs text-gray-500 mb-3">Work objects created from the digest (files in coordination/intents)</div>
          <div className="space-y-2">
            {intents.length === 0 && <div className="text-gray-500 text-sm">No intents yet. Run the digest.</div>}
            {intents.slice(0, 12).map((i, idx) => (
              <div key={idx} className="bg-white/5 border border-white/10 rounded-lg p-3">
                <div className="flex justify-between">
                  <div className="text-sm font-bold text-gray-200">{i.intent_type || "intent"} • {i.droplet_name || "unknown"}</div>
                  <div className="text-xs text-gray-500">{i.score ?? ""}</div>
                </div>
                <div className="text-xs text-gray-400 mt-1">{i.file}</div>
                <div className="text-xs text-gray-500 mt-1">expires: {i.expires_at || "unknown"}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="glass rounded-xl p-6">
          <h3 className="font-bold text-yellow-300 flex items-center gap-2 mb-4"><Clock size={16}/> RECENT OUTCOMES</h3>
          <div className="text-xs text-gray-500 mb-3">Real-world feedback that trains the next digest.</div>
          <div className="space-y-2">
            {outcomes.length === 0 && <div className="text-gray-500 text-sm">No outcomes recorded yet.</div>}
            {outcomes.slice(0, 12).map((o, idx) => (
              <div key={idx} className="bg-white/5 border border-white/10 rounded-lg p-3">
                <div className="flex justify-between">
                  <div className="text-sm font-bold text-gray-200">{o.category} • {o.outcome}</div>
                  <div className="text-xs text-gray-500">{o.recorded_at}</div>
                </div>
                <div className="text-xs text-gray-300 mt-1">{o.action_title}</div>
                {(o.metric_name || o.metric_value !== null) && (
                  <div className="text-xs text-gray-500 mt-1">{o.metric_name}: {o.metric_value}</div>
                )}
                {o.notes && <div className="text-xs text-gray-500 mt-1">{o.notes}</div>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function TreasuryView({ data }) {
  if (!data) return <div className="flex justify-center items-center h-full text-gray-500">Loading Financial Data...</div>
  
  return (
    <div className="h-full flex flex-col space-y-6">
       {/* TOP ROW: HEADLINES */}
       <div className="grid grid-cols-4 gap-6">
          <Card title="Total Value Locked" value={`$${data.tvl.toLocaleString()}`} icon={DollarSign} color="text-yellow-400" sub={`+${data.pnl_24h} (24h)`} />
          <Card title="Liquid Cash" value={`$${data.cash.toLocaleString()}`} icon={Inbox} color="text-green-400" sub={`${data.allocation.stable}% of Portfolio`} />
          <Card title="24h PnL" value={`+${data.pnl_percent}%`} icon={TrendingUp} color="text-blue-400" sub="Outperforming Market" />
          <Card title="Risk Score" value="LOW" icon={Shield} color="text-green-400" sub="No Liquidation Risk" />
       </div>

       {/* MIDDLE ROW: MAGNET ENGINE & POSITIONS */}
       <div className="flex-1 flex gap-6 overflow-hidden">
          
          {/* MAGNET ENGINE CARD */}
          <div className="w-1/3 glass rounded-xl p-6 flex flex-col relative overflow-hidden border border-purple-500/30">
              <div className="absolute top-0 left-0 w-full h-1 bg-purple-500 animate-pulse" />
              <h3 className="font-bold text-purple-400 mb-6 flex items-center gap-2"><Zap size={16}/> MAGNET ENGINE v2.0</h3>
              
              <div className="space-y-6">
                  <div className="flex justify-between items-end">
                      <span className="text-gray-400 text-sm">STATUS</span>
                      <span className="text-xl font-bold text-yellow-400 animate-pulse">{data.magnet_engine?.status || "OFFLINE"}</span>
                  </div>
                  <div className="bg-black/20 p-4 rounded border border-white/10 font-mono text-xs space-y-2">
                      <div className="flex justify-between"><span>STRENGTH (S)</span><span className="text-green-400">{data.magnet_engine?.magnet_strength || 0}</span></div>
                      <div className="flex justify-between"><span>DISTANCE (D)</span><span className="text-blue-400">{data.magnet_engine?.distance || 0}</span></div>
                      <div className="flex justify-between"><span>CONFLICT (C)</span><span className="text-red-400">{data.magnet_engine?.conflict || 0}</span></div>
                      <div className="flex justify-between"><span>VOLATILITY (V)</span><span className="text-orange-400">{data.magnet_engine?.volatility || 0}</span></div>
                      <div className="h-px bg-white/10 my-2" />
                      <div className="flex justify-between text-sm font-bold"><span>LEVERAGE (L)</span><span className="text-purple-400">{data.magnet_engine?.leverage || 1.0}x</span></div>
                  </div>
                  <div className="text-center text-[10px] text-gray-500">{data.magnet_engine?.message || "System Initializing..."}</div>
              </div>
          </div>

          {/* POSITIONS LIST */}
          <div className="w-2/3 glass rounded-xl p-6 flex flex-col">
              <h3 className="font-bold text-yellow-400 mb-4 flex items-center gap-2"><Activity size={16}/> ACTIVE POSITIONS</h3>
              <div className="overflow-y-auto flex-1">
                <table className="w-full text-left text-sm">
                    <thead className="text-gray-500 border-b border-white/10 sticky top-0 bg-[#0a0a0f]">
                      <tr>
                          <th className="pb-3">ASSET</th>
                          <th className="pb-3">PROTOCOL</th>
                          <th className="pb-3">SIZE (USD)</th>
                          <th className="pb-3">APY</th>
                          <th className="pb-3">RISK</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {data.positions.map((pos, i) => (
                          <tr key={i} className="hover:bg-white/5 transition">
                            <td className="py-4 font-bold">{pos.asset}</td>
                            <td className="py-4 text-gray-400">{pos.protocol}</td>
                            <td className="py-4">${pos.size_usd.toLocaleString()}</td>
                            <td className="py-4 text-green-400">{(pos.apy * 100).toFixed(1)}%</td>
                            <td className="py-4">
                                <span className={`px-2 py-1 rounded text-xs ${pos.risk === 'HIGH' ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>
                                  {pos.risk}
                                </span>
                            </td>
                          </tr>
                      ))}
                    </tbody>
                </table>
              </div>
          </div>
       </div>
    </div>
  )
}

function Card({ title, value, icon: Icon, color, sub }) {
  return (
    <div className="glass p-6 rounded-xl border-t-2 border-white/10 hover:border-purple-500/50 transition">
       <div className="flex justify-between items-start mb-4">
          <span className="text-xs text-gray-400 tracking-wider">{title}</span>
          <Icon size={20} className={color} />
       </div>
       <div className={`text-2xl font-bold mb-1 ${color}`}>{value}</div>
       <div className="text-xs text-gray-500">{sub}</div>
    </div>
  )
}

// --- COMMONS MINISTRY VIEW ---
function CommonsView({ data, onRefresh }) {
  if (!data) return (
    <div className="flex flex-col justify-center items-center h-full text-gray-500">
      <HeartHandshake size={48} className="mb-4 opacity-30" />
      <p>Loading Commons Ministry Data...</p>
      <p className="text-xs mt-2">Trust Index • Contributions • Needs Allocation</p>
    </div>
  )
  
  // Calculate posture color
  const postureColors = {
    emergency: 'text-red-500',
    conservative: 'text-yellow-500',
    balanced: 'text-blue-400',
    generous: 'text-green-400'
  }
  
  const postureColor = postureColors[data.trust_index?.policy_posture] || 'text-gray-400'
  const trustIndex = data.trust_index?.trust_index || 0
  const posture = data.trust_index?.policy_posture || 'unknown'
  
  return (
    <div className="h-full flex flex-col space-y-6">
      {/* TOP ROW: Trust Index Ring + Stats */}
      <div className="grid grid-cols-4 gap-6">
        {/* Trust Index Ring */}
        <div className="glass rounded-xl p-6 flex flex-col items-center justify-center relative border border-purple-500/30">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-500 via-blue-500 to-green-500" />
          <div className="relative w-32 h-32">
            <svg className="transform -rotate-90 w-32 h-32">
              <circle cx="64" cy="64" r="56" strokeWidth="8" stroke="rgba(255,255,255,0.1)" fill="none" />
              <circle 
                cx="64" cy="64" r="56" strokeWidth="8" 
                stroke={trustIndex > 0.7 ? '#22c55e' : trustIndex > 0.3 ? '#3b82f6' : '#ef4444'}
                fill="none" 
                strokeDasharray={`${trustIndex * 352} 352`}
                strokeLinecap="round"
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-bold">{(trustIndex * 100).toFixed(0)}%</span>
              <span className="text-xs text-gray-400">TRUST INDEX</span>
            </div>
          </div>
          <div className={`mt-4 font-bold uppercase ${postureColor}`}>{posture}</div>
        </div>
        
        <Card title="Solvency (THS)" value={`${((data.trust_index?.components?.solvency?.raw_value || 0) * 100).toFixed(0)}%`} icon={Shield} color="text-green-400" sub={data.trust_index?.components?.solvency?.details?.mode || 'N/A'} />
        <Card title="Commons Health" value={`${((data.trust_index?.components?.commons_health?.score || 0) * 100).toFixed(0)}%`} icon={Layers} color="text-blue-400" sub={`Reserve: $${(data.trust_index?.components?.commons_health?.details?.reserve_value || 0).toLocaleString()}`} />
        <Card title="Participation" value={`${((data.trust_index?.components?.participation?.score || 0) * 100).toFixed(0)}%`} icon={Users} color="text-purple-400" sub={`${data.trust_index?.components?.participation?.details?.total_members || 0} members`} />
      </div>

      {/* MIDDLE ROW: Contributions + Needs */}
      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Contribution Stats */}
        <div className="w-1/2 glass rounded-xl p-6 flex flex-col border border-purple-500/20">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-purple-400 flex items-center gap-2"><CircleDot size={16}/> CONTRIBUTION TRACKER</h3>
            <button onClick={onRefresh} className="text-gray-500 hover:text-white transition-colors"><RefreshCw size={14}/></button>
          </div>
          
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-black/20 p-4 rounded border border-white/10 text-center">
              <div className="text-2xl font-bold text-purple-400">{data.contributions?.total_members || 0}</div>
              <div className="text-xs text-gray-500">Total Members</div>
            </div>
            <div className="bg-black/20 p-4 rounded border border-white/10 text-center">
              <div className="text-2xl font-bold text-green-400">{data.contributions?.active_contributors || 0}</div>
              <div className="text-xs text-gray-500">Active Contributors</div>
            </div>
            <div className="bg-black/20 p-4 rounded border border-white/10 text-center">
              <div className="text-2xl font-bold text-blue-400">{data.contributions?.total_trust_issued || 0}</div>
              <div className="text-xs text-gray-500">TRUST Issued</div>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            <h4 className="text-sm text-gray-400 mb-2">Contribution by Type</h4>
            {Object.entries(data.contributions?.by_type || {}).map(([type, score]) => (
              <div key={type} className="flex justify-between py-2 border-b border-white/5 text-sm">
                <span className="capitalize text-gray-300">{type}</span>
                <span className="text-purple-400">{score} TRUST</span>
              </div>
            ))}
          </div>
        </div>

        {/* Needs Allocation */}
        <div className="w-1/2 glass rounded-xl p-6 flex flex-col border border-green-500/20">
          <h3 className="font-bold text-green-400 mb-4 flex items-center gap-2"><HeartHandshake size={16}/> NEEDS ALLOCATION</h3>
          
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-black/20 p-4 rounded border border-white/10 text-center">
              <div className="text-2xl font-bold text-green-400">${(data.budget?.monthly_budget_uc || 0).toLocaleString()}</div>
              <div className="text-xs text-gray-500">Monthly Budget</div>
            </div>
            <div className="bg-black/20 p-4 rounded border border-white/10 text-center">
              <div className="text-2xl font-bold text-yellow-400">${(data.needs?.total_committed_uc || 0).toLocaleString()}</div>
              <div className="text-xs text-gray-500">Committed Needs</div>
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            <h4 className="text-sm text-gray-400 mb-2">Budget by Category</h4>
            {Object.entries(data.budget?.categories || {}).map(([cat, info]) => (
              <div key={cat} className="mb-3">
                <div className="flex justify-between text-sm mb-1">
                  <span className="capitalize text-gray-300">{cat}</span>
                  <span className="text-green-400">${info.available?.toFixed(0) || 0} / ${info.budget?.toFixed(0) || 0}</span>
                </div>
                <div className="h-2 bg-black/30 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-green-500 to-green-400" 
                    style={{ width: `${Math.min(100, (info.used / info.budget) * 100 || 0)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* BOTTOM: Policy Info */}
      <div className="glass rounded-xl p-4 border border-white/10">
        <div className="flex justify-between items-center text-sm">
          <div className="flex items-center gap-6">
            <span className="text-gray-500">Policy Posture: <span className={`font-bold uppercase ${postureColor}`}>{posture}</span></span>
            <span className="text-gray-500">Safety Buffer: <span className="text-white">{data.policy?.parameters?.safety_buffer || 1.5}x</span></span>
            <span className="text-gray-500">Max Allocation: <span className="text-white">{((data.policy?.parameters?.max_single_allocation || 0) * 100).toFixed(0)}%</span></span>
          </div>
          <div className="text-gray-500 text-xs">
            Last Update: {data.trust_index?.timestamp ? new Date(data.trust_index.timestamp).toLocaleTimeString() : 'N/A'}
          </div>
        </div>
      </div>
    </div>
  )
}

// --- MISSION CONTROL VIEW ---
function MissionControlView({ stats, tokens, tasks }) {
  const [showModal, setShowModal] = useState(false)
  const [tokenName, setTokenName] = useState("")
  const [tokenType, setTokenType] = useState("assistant")
  const [tokenExpiry, setTokenExpiry] = useState("24")
  const [copiedToken, setCopiedToken] = useState(null)

  const createToken = async (e) => {
    e.preventDefault()
    const res = await fetch(`${API_URL}/mission-control/tokens`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: tokenName, type: tokenType, expires_hours: tokenExpiry })
    })
    const newToken = await res.json()
    setCopiedToken(newToken.id)
    setShowModal(false)
    setTokenName("")
  }

  const revokeToken = async (id) => {
    await fetch(`${API_URL}/mission-control/tokens/${id}`, { method: 'DELETE' })
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    setCopiedToken(text)
    setTimeout(() => setCopiedToken(null), 2000)
  }

  const activeTokens = tokens.filter(t => t.active)
  const pendingTasks = tasks.filter(t => t.status === 'pending')

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-6">
        <Card title="Active Tokens" value={stats.active_tokens} icon={Key} color="text-cyan-400" sub="Developers & Assistants" />
        <Card title="Pending Tasks" value={stats.pending_tasks} icon={Clock} color="text-yellow-400" sub="API signups needed" />
        <Card title="Blocked Services" value={stats.blocked_services} icon={Shield} color="text-red-400" sub="Waiting for APIs" />
        <Card title="Completed" value={stats.completed_tasks} icon={Check} color="text-green-400" sub="APIs acquired" />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Tokens Panel */}
        <div className="w-1/3 glass rounded-xl p-6 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-cyan-400 flex items-center gap-2"><Key size={16}/> ACCESS TOKENS</h3>
            <button onClick={() => setShowModal(true)} className="bg-purple-600 hover:bg-purple-700 px-3 py-1 rounded text-xs font-bold flex items-center gap-1">
              <Plus size={12}/> NEW
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-3">
            {activeTokens.length === 0 ? (
              <div className="text-center text-gray-500 py-8">No active tokens. Create one to give access to developers or assistants.</div>
            ) : (
              activeTokens.map(token => (
                <div key={token.id} className="bg-white/5 p-4 rounded-lg border border-white/10">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <div className="font-bold text-sm">{token.name}</div>
                      <div className="text-xs text-gray-500">{token.type === 'developer' ? '🧑‍💻 Developer' : '🤖 Assistant'}</div>
                    </div>
                    <button onClick={() => revokeToken(token.id)} className="text-red-400 hover:text-red-300 text-xs">Revoke</button>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <code className="text-[10px] bg-black/30 px-2 py-1 rounded flex-1 truncate">{token.id}</code>
                    <button onClick={() => copyToClipboard(token.id)} className="text-cyan-400 hover:text-cyan-300">
                      {copiedToken === token.id ? <Check size={14}/> : <Copy size={14}/>}
                    </button>
                  </div>
                  {token.expires_at && (
                    <div className="text-[10px] text-gray-500 mt-2">Expires: {new Date(token.expires_at).toLocaleDateString()}</div>
                  )}
                </div>
              ))
            )}
          </div>

          {/* Portal Links */}
          <div className="mt-4 pt-4 border-t border-white/10 space-y-2">
            <div className="text-xs text-gray-400 mb-2">SHARE PORTAL LINKS:</div>
            <a href="/portal/developer" target="_blank" className="flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300">
              <ExternalLink size={14}/> Developer Portal
            </a>
            <a href="/portal/assistant" target="_blank" className="flex items-center gap-2 text-sm text-yellow-400 hover:text-yellow-300">
              <ExternalLink size={14}/> Assistant Portal
            </a>
          </div>
        </div>

        {/* Tasks Panel */}
        <div className="w-2/3 glass rounded-xl p-6 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-yellow-400 flex items-center gap-2"><Activity size={16}/> API TASKS QUEUE</h3>
            <span className="text-xs text-gray-500">{pendingTasks.length} pending</span>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            {pendingTasks.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-2">🎉</div>
                All caught up! No pending API tasks.
              </div>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="text-gray-500 border-b border-white/10 sticky top-0 bg-[#0a0a0f]">
                  <tr>
                    <th className="pb-3">Priority</th>
                    <th className="pb-3">API</th>
                    <th className="pb-3">Service</th>
                    <th className="pb-3">Blocking</th>
                    <th className="pb-3">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {pendingTasks.map((task, i) => (
                    <tr key={task.id} className="hover:bg-white/5 transition">
                      <td className="py-3">
                        <span className={`px-2 py-1 rounded text-xs font-bold ${task.priority > 300 ? 'bg-red-500/20 text-red-400' : task.priority > 100 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'}`}>
                          {task.priority}
                        </span>
                      </td>
                      <td className="py-3 font-bold">{task.api_name}</td>
                      <td className="py-3 text-gray-400">{task.service}</td>
                      <td className="py-3">
                        {task.blocking_services?.length > 0 ? (
                          <span className="text-red-400">{task.blocking_services.length} services</span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="py-3 text-gray-400">{task.estimated_time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Create Token Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center backdrop-blur-sm">
          <div className="bg-god-card border border-white/20 p-8 rounded-xl w-[450px]">
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2"><Key size={20}/> Create Access Token</h3>
            <form onSubmit={createToken} className="space-y-4">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Name</label>
                <input 
                  value={tokenName} 
                  onChange={e => setTokenName(e.target.value)} 
                  className="w-full bg-black/40 border border-white/10 rounded p-3" 
                  placeholder="e.g., Maria - API Assistant" 
                  required 
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Type</label>
                <select 
                  value={tokenType}
                  onChange={e => setTokenType(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded p-3"
                >
                  <option value="assistant">🤖 Assistant (API signup tasks)</option>
                  <option value="developer">🧑‍💻 Developer (Code access)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Expires In</label>
                <select 
                  value={tokenExpiry}
                  onChange={e => setTokenExpiry(e.target.value)}
                  className="w-full bg-black/40 border border-white/10 rounded p-3"
                >
                  <option value="24">24 hours</option>
                  <option value="48">48 hours</option>
                  <option value="168">1 week</option>
                  <option value="720">30 days</option>
                  <option value="">Never</option>
                </select>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setShowModal(false)} className="text-gray-400 px-4 py-2">Cancel</button>
                <button type="submit" className="bg-purple-600 px-6 py-2 rounded font-bold">Create Token</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// --- TEAM HUB VIEW ---
function TeamHubView({ stats, humans, activity, recommendations, tokens }) {
  const [showAddModal, setShowAddModal] = useState(false)
  const [showAssignModal, setShowAssignModal] = useState(false)
  const [selectedHuman, setSelectedHuman] = useState(null)
  const [newHuman, setNewHuman] = useState({ name: '', email: '', specialty: 'api', contact_channel: 'email', notes: '' })

  const addHuman = async (e) => {
    e.preventDefault()
    await fetch(`${API_URL}/team/humans`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newHuman)
    })
    setShowAddModal(false)
    setNewHuman({ name: '', email: '', specialty: 'api', contact_channel: 'email', notes: '' })
    // Refresh will happen via WebSocket
  }

  const assignToken = async (humanId, tokenType, hours) => {
    const res = await fetch(`${API_URL}/team/assign-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ human_id: humanId, type: tokenType, expires_hours: hours })
    })
    const data = await res.json()
    if (data.portal_url) {
      navigator.clipboard.writeText(window.location.origin + data.portal_url)
      alert(`Token created! Portal URL copied to clipboard.`)
    }
    setShowAssignModal(false)
    setSelectedHuman(null)
  }

  const TrustStars = ({ level }) => (
    <div className="flex gap-0.5">
      {[1,2,3,4,5].map(i => (
        <Star key={i} size={12} className={i <= level ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'} />
      ))}
    </div>
  )

  const getSpecialtyColor = (s) => {
    const colors = { api: 'text-cyan-400', dev: 'text-purple-400', design: 'text-pink-400', general: 'text-gray-400' }
    return colors[s] || colors.general
  }

  const getSpecialtyIcon = (s) => {
    const icons = { api: '🔌', dev: '💻', design: '🎨', general: '🔧' }
    return icons[s] || icons.general
  }

  return (
    <div className="h-full flex flex-col space-y-6">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-6">
        <Card title="Team Size" value={stats.total_humans} icon={Users} color="text-cyan-400" sub={`${stats.active_humans} active`} />
        <Card title="Working Now" value={stats.working_now} icon={Activity} color="text-green-400" sub="With active tokens" />
        <Card title="Active Tokens" value={stats.active_tokens} icon={Key} color="text-yellow-400" sub="Assigned to humans" />
        <Card title="Credits Earned" value={stats.total_credits_earned?.toLocaleString() || 0} icon={Award} color="text-purple-400" sub="Total by team" />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-6 overflow-hidden">
        
        {/* Trusted Humans Panel */}
        <div className="w-1/2 glass rounded-xl p-6 flex flex-col">
          <div className="flex justify-between items-center mb-4">
            <h3 className="font-bold text-cyan-400 flex items-center gap-2"><Users size={16}/> TRUSTED HUMANS</h3>
            <button onClick={() => setShowAddModal(true)} className="bg-purple-600 hover:bg-purple-700 px-3 py-1 rounded text-xs font-bold flex items-center gap-1">
              <UserPlus size={12}/> ADD
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-3">
            {humans.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                <div className="text-4xl mb-2">👥</div>
                No trusted humans yet. Add your first team member to get started.
              </div>
            ) : (
              humans.map(human => (
                <div key={human.id} className="bg-white/5 p-4 rounded-lg border border-white/10 hover:border-purple-500/50 transition">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center text-lg">
                        {getSpecialtyIcon(human.specialty)}
                      </div>
                      <div>
                        <div className="font-bold">{human.name}</div>
                        <div className={`text-xs ${getSpecialtyColor(human.specialty)}`}>{human.specialty?.toUpperCase()}</div>
                      </div>
                    </div>
                    <TrustStars level={human.trust_level || 1} />
                  </div>
                  
                  <div className="grid grid-cols-3 gap-2 text-xs mt-3 mb-3">
                    <div className="bg-black/20 p-2 rounded text-center">
                      <div className="text-green-400 font-bold">{human.tasks_completed || 0}</div>
                      <div className="text-gray-500">Completed</div>
                    </div>
                    <div className="bg-black/20 p-2 rounded text-center">
                      <div className="text-red-400 font-bold">{human.tasks_failed || 0}</div>
                      <div className="text-gray-500">Failed</div>
                    </div>
                    <div className="bg-black/20 p-2 rounded text-center">
                      <div className="text-yellow-400 font-bold">{human.credits_earned || 0}</div>
                      <div className="text-gray-500">Credits</div>
                    </div>
                  </div>
                  
                  <div className="flex gap-2">
                    <button 
                      onClick={() => { setSelectedHuman(human); setShowAssignModal(true) }}
                      className="flex-1 bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-400 py-2 rounded text-xs font-bold flex items-center justify-center gap-1"
                    >
                      <Key size={12}/> Assign Token
                    </button>
                    <button className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded text-xs text-gray-400">
                      Edit
                    </button>
                  </div>
                  
                  {human.last_active && (
                    <div className="text-[10px] text-gray-600 mt-2">
                      Last active: {new Date(human.last_active).toLocaleDateString()}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Recommendations + Activity */}
        <div className="w-1/2 flex flex-col gap-6">
          
          {/* AI Recommendations */}
          <div className="glass rounded-xl p-6 flex-1 flex flex-col">
            <h3 className="font-bold text-yellow-400 flex items-center gap-2 mb-4"><Brain size={16}/> AI RECOMMENDATIONS</h3>
            
            <div className="flex-1 overflow-y-auto space-y-3">
              {recommendations.length === 0 ? (
                <div className="text-center text-gray-500 py-4">
                  <div className="text-2xl mb-2">🤖</div>
                  Add humans and pending tasks to see AI recommendations.
                </div>
              ) : (
                recommendations.map((rec, i) => (
                  <div key={i} className="bg-white/5 p-4 rounded-lg border border-yellow-500/20">
                    <div className="flex justify-between items-start mb-2">
                      <div className="font-bold text-sm">{rec.task?.api_name || 'Unknown Task'}</div>
                      <span className={`text-xs px-2 py-1 rounded ${rec.confidence >= 80 ? 'bg-green-500/20 text-green-400' : rec.confidence >= 50 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'}`}>
                        {rec.confidence}% match
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-300">
                      <span>Assign to:</span>
                      <span className="font-bold text-cyan-400">{rec.recommended_human?.name}</span>
                      <TrustStars level={rec.recommended_human?.trust_level || 1} />
                    </div>
                    <div className="text-xs text-gray-500 mt-1">{rec.reason}</div>
                    <button 
                      onClick={() => { setSelectedHuman(rec.recommended_human); setShowAssignModal(true) }}
                      className="mt-3 w-full bg-yellow-600/20 hover:bg-yellow-600/40 text-yellow-400 py-2 rounded text-xs font-bold"
                    >
                      Approve & Assign
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="glass rounded-xl p-6 h-48 flex flex-col">
            <h3 className="font-bold text-gray-400 flex items-center gap-2 mb-4"><Activity size={16}/> RECENT ACTIVITY</h3>
            <div className="flex-1 overflow-y-auto space-y-2">
              {activity.length === 0 ? (
                <div className="text-center text-gray-600 text-sm">No activity yet</div>
              ) : (
                activity.slice().reverse().slice(0, 10).map((a, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className={`w-2 h-2 rounded-full ${a.action.includes('complete') ? 'bg-green-500' : a.action.includes('fail') ? 'bg-red-500' : 'bg-blue-500'}`} />
                    <span className="text-gray-400">{a.action.replace(/_/g, ' ')}</span>
                    {a.details?.name && <span className="text-white">{a.details.name}</span>}
                    <span className="text-gray-600 ml-auto">{new Date(a.timestamp).toLocaleTimeString()}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Add Human Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center backdrop-blur-sm">
          <div className="bg-god-card border border-white/20 p-8 rounded-xl w-[500px]">
            <h3 className="text-xl font-bold mb-6 flex items-center gap-2"><UserPlus size={20}/> Add Trusted Human</h3>
            <form onSubmit={addHuman} className="space-y-4">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Name *</label>
                <input 
                  value={newHuman.name} 
                  onChange={e => setNewHuman({...newHuman, name: e.target.value})} 
                  className="w-full bg-black/40 border border-white/10 rounded p-3" 
                  placeholder="e.g., Maria Rodriguez" 
                  required 
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Email</label>
                <input 
                  value={newHuman.email} 
                  onChange={e => setNewHuman({...newHuman, email: e.target.value})} 
                  className="w-full bg-black/40 border border-white/10 rounded p-3" 
                  placeholder="maria@example.com" 
                  type="email"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Specialty</label>
                  <select 
                    value={newHuman.specialty}
                    onChange={e => setNewHuman({...newHuman, specialty: e.target.value})}
                    className="w-full bg-black/40 border border-white/10 rounded p-3"
                  >
                    <option value="api">🔌 API Integrations</option>
                    <option value="dev">💻 Development</option>
                    <option value="design">🎨 Design</option>
                    <option value="general">🔧 General</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-400 mb-1 block">Contact Channel</label>
                  <select 
                    value={newHuman.contact_channel}
                    onChange={e => setNewHuman({...newHuman, contact_channel: e.target.value})}
                    className="w-full bg-black/40 border border-white/10 rounded p-3"
                  >
                    <option value="email">📧 Email</option>
                    <option value="slack">💬 Slack</option>
                    <option value="fiverr">🟢 Fiverr</option>
                    <option value="upwork">🟩 Upwork</option>
                    <option value="whatsapp">📱 WhatsApp</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Notes</label>
                <textarea 
                  value={newHuman.notes} 
                  onChange={e => setNewHuman({...newHuman, notes: e.target.value})} 
                  className="w-full bg-black/40 border border-white/10 rounded p-3 h-20" 
                  placeholder="Any notes about this person..."
                />
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setShowAddModal(false)} className="text-gray-400 px-4 py-2">Cancel</button>
                <button type="submit" className="bg-purple-600 px-6 py-2 rounded font-bold">Add Human</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Assign Token Modal */}
      {showAssignModal && selectedHuman && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center backdrop-blur-sm">
          <div className="bg-god-card border border-white/20 p-8 rounded-xl w-[450px]">
            <h3 className="text-xl font-bold mb-2 flex items-center gap-2"><Key size={20}/> Assign Token</h3>
            <p className="text-gray-400 mb-6">Create access token for <span className="text-cyan-400 font-bold">{selectedHuman.name}</span></p>
            
            <div className="space-y-4">
              <div className="bg-white/5 p-4 rounded-lg">
                <div className="text-xs text-gray-400 mb-2">TOKEN TYPE</div>
                <div className="grid grid-cols-2 gap-3">
                  <button 
                    onClick={() => assignToken(selectedHuman.id, 'assistant', 24)}
                    className="bg-yellow-600/20 hover:bg-yellow-600/40 text-yellow-400 p-4 rounded-lg text-center"
                  >
                    <div className="text-2xl mb-1">🤖</div>
                    <div className="font-bold">Assistant</div>
                    <div className="text-xs opacity-70">API signup tasks</div>
                  </button>
                  <button 
                    onClick={() => assignToken(selectedHuman.id, 'developer', 48)}
                    className="bg-purple-600/20 hover:bg-purple-600/40 text-purple-400 p-4 rounded-lg text-center"
                  >
                    <div className="text-2xl mb-1">💻</div>
                    <div className="font-bold">Developer</div>
                    <div className="text-xs opacity-70">Code access</div>
                  </button>
                </div>
              </div>
              
              <div className="text-xs text-gray-500 text-center">
                Token will be created and portal URL copied to clipboard
              </div>
            </div>
            
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={() => { setShowAssignModal(false); setSelectedHuman(null) }} className="text-gray-400 px-4 py-2">Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// --- SYSTEM INTELLIGENCE VIEW ---
function SystemIntelligenceView({ data, onRefresh }) {
  if (!data) return (
    <div className="flex justify-center items-center h-full text-gray-500">
      <div className="text-center">
        <RefreshCw className="animate-spin mx-auto mb-4" size={32} />
        <div>Loading System Intelligence...</div>
      </div>
    </div>
  )

  const traits = data.traits || {}
  const status = data.status || {}
  const awareness = data.awareness || {}
  const resilience = data.resilience || {}
  const resources = data.resources || {}
  const notifications = data.notifications || []

  const healthPercent = status.services_total > 0 
    ? Math.round((status.services_healthy / status.services_total) * 100) 
    : 0

  const getStatusColor = (level) => {
    if (level === 'normal') return 'text-green-400'
    if (level === 'reduced') return 'text-yellow-400'
    if (level === 'minimal') return 'text-orange-400'
    return 'text-red-400'
  }

  return (
    <div className="h-full flex flex-col space-y-6 overflow-y-auto">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold flex items-center gap-3">
          <Eye className="text-cyan-400" /> SYSTEM INTELLIGENCE
        </h2>
        <button onClick={onRefresh} className="bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-400 px-4 py-2 rounded flex items-center gap-2 text-sm">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-5 gap-4">
        <div className="glass p-4 rounded-xl border-l-4 border-cyan-500">
          <div className="text-xs text-gray-400 mb-1">ECOSYSTEM HEALTH</div>
          <div className="text-2xl font-bold text-cyan-400">{status.ecosystem_health?.toFixed(0) || 0}%</div>
          <div className="text-xs text-gray-500">{status.operational_status}</div>
        </div>
        <div className="glass p-4 rounded-xl border-l-4 border-green-500">
          <div className="text-xs text-gray-400 mb-1">SERVICES</div>
          <div className="text-2xl font-bold text-green-400">{status.services_healthy}/{status.services_total}</div>
          <div className="text-xs text-gray-500">{healthPercent}% healthy</div>
        </div>
        <div className={`glass p-4 rounded-xl border-l-4 ${status.degradation_level === 'normal' ? 'border-green-500' : 'border-yellow-500'}`}>
          <div className="text-xs text-gray-400 mb-1">DEGRADATION</div>
          <div className={`text-2xl font-bold ${getStatusColor(status.degradation_level)}`}>{status.degradation_level?.toUpperCase()}</div>
          <div className="text-xs text-gray-500">System mode</div>
        </div>
        <div className="glass p-4 rounded-xl border-l-4 border-purple-500">
          <div className="text-xs text-gray-400 mb-1">AWARENESS</div>
          <div className="text-2xl font-bold text-purple-400">{awareness.services_monitored || 0}</div>
          <div className="text-xs text-gray-500">services monitored</div>
        </div>
        <div className="glass p-4 rounded-xl border-l-4 border-yellow-500">
          <div className="text-xs text-gray-400 mb-1">PREDICTIONS</div>
          <div className="text-2xl font-bold text-yellow-400">{awareness.active_predictions || 0}</div>
          <div className="text-xs text-gray-500">active alerts</div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-6 min-h-0">
        
        {/* Left Column: Traits + Providers */}
        <div className="w-1/3 flex flex-col gap-6">
          {/* System Traits */}
          <div className="glass rounded-xl p-6 flex-1">
            <h3 className="font-bold text-cyan-400 flex items-center gap-2 mb-4"><Heart size={16}/> SYSTEM TRAITS</h3>
            <div className="space-y-3">
              {Object.entries(traits).map(([trait, enabled]) => (
                <div key={trait} className="flex items-center justify-between">
                  <span className="text-sm text-gray-300">{trait.replace(/_/g, ' ')}</span>
                  <span className={`w-3 h-3 rounded-full ${enabled ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-gray-600'}`} />
                </div>
              ))}
            </div>
          </div>

          {/* Provider Failover */}
          <div className="glass rounded-xl p-6">
            <h3 className="font-bold text-purple-400 flex items-center gap-2 mb-4"><Server size={16}/> PROVIDER FAILOVER</h3>
            <div className="space-y-4">
              {Object.entries(resilience.providers || {}).map(([category, providers]) => (
                <div key={category}>
                  <div className="text-xs text-gray-500 mb-2">{category.toUpperCase()}</div>
                  <div className="flex flex-wrap gap-2">
                    {providers.map((p, i) => (
                      <span 
                        key={p.name} 
                        className={`text-xs px-2 py-1 rounded ${p.available ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'} ${i === 0 ? 'ring-1 ring-white/20' : ''}`}
                      >
                        {p.name} {p.is_backup && '(backup)'}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Middle Column: Predictions + Resources */}
        <div className="w-1/3 flex flex-col gap-6">
          {/* Active Predictions */}
          <div className="glass rounded-xl p-6 flex-1 overflow-hidden flex flex-col">
            <h3 className="font-bold text-yellow-400 flex items-center gap-2 mb-4"><AlertTriangle size={16}/> PREDICTIONS</h3>
            <div className="flex-1 overflow-y-auto space-y-3">
              {(awareness.top_predictions || []).slice(0, 5).map((pred, i) => (
                <div key={i} className="bg-white/5 p-3 rounded-lg border-l-2 border-yellow-500">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs text-yellow-400">{pred.type}</span>
                    <span className="text-xs text-gray-500">{Math.round(pred.confidence * 100)}%</span>
                  </div>
                  <div className="text-sm text-gray-300">{pred.description}</div>
                  <div className="text-xs text-gray-500 mt-1">{pred.service}</div>
                </div>
              ))}
              {(!awareness.top_predictions || awareness.top_predictions.length === 0) && (
                <div className="text-center text-gray-500 py-4">No active predictions</div>
              )}
            </div>
          </div>

          {/* Resources */}
          <div className="glass rounded-xl p-6">
            <h3 className="font-bold text-blue-400 flex items-center gap-2 mb-4"><Cpu size={16}/> RESOURCES</h3>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-400">Memory</span>
                  <span className="text-blue-400">{resources.latest?.memory_percent || 0}%</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div 
                    className={`h-full transition-all ${resources.latest?.memory_percent > 80 ? 'bg-red-500' : resources.latest?.memory_percent > 60 ? 'bg-yellow-500' : 'bg-blue-500'}`}
                    style={{ width: `${resources.latest?.memory_percent || 0}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-400">Active Connections</span>
                  <span className="text-green-400">{resources.latest?.active_connections || 0}</span>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="bg-white/5 p-2 rounded text-center">
                  <div className="text-gray-500">Memory</div>
                  <div className={`font-bold ${resources.trends?.memory === 'increasing' ? 'text-red-400' : resources.trends?.memory === 'decreasing' ? 'text-green-400' : 'text-gray-400'}`}>
                    {resources.trends?.memory || 'stable'}
                  </div>
                </div>
                <div className="bg-white/5 p-2 rounded text-center">
                  <div className="text-gray-500">Requests</div>
                  <div className="text-gray-400">{resources.trends?.request_rate || 'stable'}</div>
                </div>
                <div className="bg-white/5 p-2 rounded text-center">
                  <div className="text-gray-500">Errors</div>
                  <div className="text-gray-400">{resources.trends?.error_rate || 'stable'}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Notifications + Scaling */}
        <div className="w-1/3 flex flex-col gap-6">
          {/* Notifications */}
          <div className="glass rounded-xl p-6 flex-1 overflow-hidden flex flex-col">
            <h3 className="font-bold text-red-400 flex items-center gap-2 mb-4">
              <AlertCircle size={16}/> NOTIFICATIONS
              {notifications.filter(n => !n.read).length > 0 && (
                <span className="bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                  {notifications.filter(n => !n.read).length}
                </span>
              )}
            </h3>
            <div className="flex-1 overflow-y-auto space-y-3">
              {notifications.slice().reverse().slice(0, 10).map((notif, i) => (
                <div key={notif.id || i} className={`p-3 rounded-lg border-l-2 ${notif.read ? 'bg-white/5 border-gray-600' : 'bg-red-500/10 border-red-500'}`}>
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs text-red-400">{notif.event_type}</span>
                    <span className="text-[10px] text-gray-500">{new Date(notif.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <div className="text-sm text-gray-300">
                    {notif.data?.recommendation || notif.data?.reason || JSON.stringify(notif.data).slice(0, 100)}
                  </div>
                </div>
              ))}
              {notifications.length === 0 && (
                <div className="text-center text-gray-500 py-4">No notifications</div>
              )}
            </div>
          </div>

          {/* Scaling Safeguards */}
          <div className="glass rounded-xl p-6">
            <h3 className="font-bold text-green-400 flex items-center gap-2 mb-4"><Shield size={16}/> SAFEGUARDS</h3>
            <div className="space-y-2">
              {(resilience.scaling?.safeguards_available || []).map((sg, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <Check size={14} className="text-green-400" />
                  <span className="text-gray-300">{sg.replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-white/10">
              <div className="text-xs text-gray-500 mb-2">ENABLED FEATURES</div>
              <div className="flex flex-wrap gap-1">
                {(resilience.degradation?.enabled_features || []).slice(0, 6).map((f, i) => (
                  <span key={i} className="text-[10px] bg-green-500/20 text-green-400 px-2 py-0.5 rounded">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function BrainView({ board, onCreate }) {
  const [showModal, setShowModal] = useState(false)
  const [name, setName] = useState("")
  const [desc, setDesc] = useState("")
  const handleSubmit = (e) => { e.preventDefault(); onCreate(name, desc); setShowModal(false); setName(""); setDesc("") }
  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold flex items-center gap-2"><Brain /> STRATEGY BOARD</h2>
        <button onClick={() => setShowModal(true)} className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded flex items-center gap-2 text-sm font-bold"><Plus size={16} /> NEW MISSION</button>
      </div>
      <div className="grid grid-cols-3 gap-6 flex-1">
        <Column title="📥 INTENT (Backlog)" items={board.intent} color="border-blue-500" />
        <Column title="⚙️ BUILDING (Active)" items={board.building} color="border-yellow-500" />
        <Column title="✅ DEPLOYED (Done)" items={board.deployed} color="border-green-500" />
      </div>
      {showModal && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center backdrop-blur-sm">
          <div className="bg-god-card border border-white/20 p-8 rounded-xl w-[500px]">
            <h3 className="text-xl font-bold mb-4">Dispatch New Mission</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <input value={name} onChange={e => setName(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded p-2" placeholder="Mission Name" required />
              <textarea value={desc} onChange={e => setDesc(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded p-2 h-24" placeholder="Objective" required />
              <div className="flex justify-end gap-2 mt-6"><button type="button" onClick={() => setShowModal(false)} className="text-gray-400">Cancel</button><button type="submit" className="bg-purple-600 px-6 py-2 rounded font-bold">Dispatch</button></div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

function Column({ title, items, color }) {
  return (
    <div className={`glass rounded-xl p-4 flex flex-col border-t-4 ${color}`}>
      <h3 className="font-bold mb-4 text-sm tracking-wider opacity-80">{title}</h3>
      <div className="flex-1 space-y-3 overflow-y-auto">
        {items.map((item, i) => (
          <div key={i} className="bg-white/5 p-3 rounded border-l-2 border-white/10 hover:bg-white/10 transition cursor-pointer group">
            <div className="font-bold text-sm mb-1 group-hover:text-purple-300">{item.title}</div>
            <div className="text-xs text-gray-400 line-clamp-2">{item.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function SystemGraph({ data }) {
  const centerX = 400; const centerY = 300; const radius = 200;
  return (
    <div className="h-full glass rounded-lg overflow-hidden relative flex flex-col">
        <h2 className="absolute top-4 left-4 text-green-400 font-bold flex gap-2 z-10"><Activity size={16} /> LIVE MAP</h2>
        <svg className="w-full h-full">
            {data.links.map((link, i) => <line key={i} x1={centerX} y1={centerY} x2={centerX + 100} y2={centerY + 100} stroke="rgba(255,255,255,0.1)" />)}
            {data.nodes.map((node, i) => {
                const angle = (i / data.nodes.length) * Math.PI * 2;
                return (
                    <g key={node.id} transform={`translate(${centerX + Math.cos(angle) * radius}, ${centerY + Math.sin(angle) * radius})`}>
                        <circle r="20" fill={node.group === 'core' ? '#9333ea' : '#22c55e'} className="animate-pulse" />
                        <text y="35" textAnchor="middle" fill="white" fontSize="10" className="opacity-70">{node.id}</text>
                    </g>
                )
            })}
            <g transform={`translate(${centerX}, ${centerY})`}><circle r="40" fill="#fff" opacity="0.1" /><text y="5" textAnchor="middle" fill="white" fontSize="12">CORE</text></g>
        </svg>
    </div>
  )
}

function InboxView({ items }) {
  if (!items || items.length === 0) return <div className="flex justify-center items-center h-full text-gray-500">All Clear</div>
  return (
    <div className="flex flex-col items-center pt-10 space-y-6">
        <h2 className="text-2xl font-bold text-blue-400 tracking-widest">PENDING APPROVALS</h2>
        {items.map((item, i) => (
            <div key={i} className="w-[600px] bg-god-card border border-white/10 rounded-xl p-6 shadow-2xl flex flex-col">
                <p className="text-lg mb-8">{item.content}</p>
                <div className="flex gap-4"><button className="flex-1 bg-green-600/20 py-3 rounded-lg font-bold text-green-400">APPROVE</button><button className="flex-1 bg-red-600/20 py-3 rounded-lg font-bold text-red-400">REJECT</button></div>
            </div>
        ))}
    </div>
  )
}

function ChatView({ messages, onSend }) {
  const [input, setInput] = useState(""); const scrollRef = useRef(null)
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight }, [messages])
  const handleSend = (e) => { e.preventDefault(); if(!input.trim()) return; onSend(input); setInput("") }
  return (
    <div className="h-full flex flex-col glass rounded-lg overflow-hidden">
       <div className="flex-1 p-6 space-y-4 overflow-y-auto" ref={scrollRef}>
          {messages.map((msg, i) => (
              <div key={i} className={`flex flex-col ${msg.sender === 'ARCHITECT' ? 'items-end' : 'items-start'}`}>
                  <div className={`p-3 rounded-xl text-sm ${msg.sender === 'ARCHITECT' ? 'bg-purple-600' : 'bg-white/10'}`}>{msg.content}</div>
                  <span className="text-[10px] text-gray-600 mt-1">{msg.sender}</span>
              </div>
          ))}
       </div>
       <form onSubmit={handleSend} className="p-4 bg-black/20 border-t border-white/10 flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)} className="flex-1 bg-transparent border border-white/20 rounded px-4 py-2 focus:outline-none focus:border-purple-500" placeholder="Command..." />
          <button type="submit" className="bg-purple-600 px-6 py-2 rounded font-bold">SEND</button>
       </form>
    </div>
  )
}

function AriaControlView({ ariaToken, setAriaToken }) {
  const [system, setSystem] = useState(null)
  const [caps, setCaps] = useState(null)
  const [unify, setUnify] = useState(null)
  const [agentNote, setAgentNote] = useState('')
  const [chatInput, setChatInput] = useState('')
  const [chatOutput, setChatOutput] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const headers = ariaToken ? { 'X-Aria-Admin-Token': ariaToken } : {}

  const saveToken = (t) => {
    setAriaToken(t)
    try { localStorage.setItem('aria_admin_token', t) } catch {}
  }

  const refresh = async () => {
    setError('')
    if (!ariaToken) { setError('Paste your Aria admin token to enable control-plane access.'); return }
    setLoading(true)
    try {
      const [sysRes, capsRes] = await Promise.all([
        fetch(`${API_URL}/aria/system`, { headers }),
        fetch(`${API_URL}/aria/capabilities`, { headers }),
      ])
      setSystem(await sysRes.json())
      setCaps(await capsRes.json())
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  const runUnifyScan = async () => {
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/unify/scan`)
      setUnify(await res.json())
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  const ingestAgentNote = async () => {
    setError('')
    if (!agentNote.trim()) return
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/unify/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: 'manual',
          title: 'Agent Note',
          summary: agentNote,
          components: [],
          recommendations: [],
          confidence: 'manual'
        })
      })
      const data = await res.json()
      setChatOutput(`Ingested note → ${JSON.stringify(data, null, 2)}`)
      setAgentNote('')
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  const send = async () => {
    setError('')
    if (!ariaToken) { setError('Paste your Aria admin token first.'); return }
    if (!chatInput.trim()) return
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/aria/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers },
        body: JSON.stringify({ message: chatInput }),
      })
      const data = await res.json()
      setChatOutput(data.response || JSON.stringify(data, null, 2))
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (ariaToken) refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="h-full grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="h-full flex flex-col glass rounded-lg overflow-hidden border border-white/10">
        <div className="p-6 border-b border-white/10 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold tracking-[0.2em] text-purple-300">ARIA CONTROL</h2>
            <p className="text-xs text-gray-400 mt-1">Single intelligence to view + operate the system.</p>
          </div>
          <button onClick={refresh} className="px-3 py-2 text-xs rounded bg-white/10 hover:bg-white/15 flex items-center gap-2">
            <RefreshCw size={14} /> {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>

        <div className="p-6 flex flex-col gap-4 flex-1 overflow-auto">
          <div>
            <label className="text-xs text-gray-400">Admin Token</label>
            <input
              value={ariaToken}
              onChange={(e) => saveToken(e.target.value)}
              placeholder="Paste token (stored locally)"
              className="mt-1 w-full bg-black/40 border border-white/10 rounded px-3 py-2 text-sm"
            />
            {error && <div className="mt-2 text-xs text-red-400">{error}</div>}
          </div>

          <div>
            <label className="text-xs text-gray-400">Chat</label>
            <textarea
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="Ask: show WhaleTrack positions, system health, restart a service…"
              className="mt-1 w-full h-24 bg-black/40 border border-white/10 rounded px-3 py-2 text-sm"
            />
            <div className="mt-2 flex gap-2 flex-wrap">
              <button onClick={send} className="bg-purple-600 px-4 py-2 rounded font-bold text-xs flex items-center gap-2">
                <Send size={14} /> SEND
              </button>
              <button onClick={runUnifyScan} className="bg-white/10 px-4 py-2 rounded text-xs">
                Unify Scan
              </button>
              <button onClick={() => setChatInput('Show WhaleTrack Live balance and positions.')} className="bg-white/10 px-4 py-2 rounded text-xs">
                WhaleTrack
              </button>
              <button onClick={() => setChatInput('Show system health and any degraded services.')} className="bg-white/10 px-4 py-2 rounded text-xs">
                Health
              </button>
            </div>
          </div>

          <div className="flex-1">
            <label className="text-xs text-gray-400">Response</label>
            <pre className="mt-1 text-xs bg-black/40 border border-white/10 rounded p-3 max-h-64 overflow-auto">{chatOutput || '(no response yet)'}</pre>
          </div>

          <div>
            <label className="text-xs text-gray-400">Agent Note → Memory (Unify)</label>
            <textarea
              value={agentNote}
              onChange={(e) => setAgentNote(e.target.value)}
              placeholder="Paste an agent’s summary of what’s real, what’s redundant, what to archive…"
              className="mt-1 w-full h-20 bg-black/40 border border-white/10 rounded px-3 py-2 text-sm"
            />
            <div className="mt-2">
              <button onClick={ingestAgentNote} className="bg-white/10 px-4 py-2 rounded text-xs">
                Ingest Note
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="h-full flex flex-col glass rounded-lg overflow-hidden border border-white/10">
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
          <h3 className="text-sm font-bold tracking-[0.2em] text-gray-200">SYSTEM SNAPSHOT</h3>
          <span className="text-[10px] text-gray-500">{system?.timestamp || ''}</span>
        </div>
        <div className="p-6 flex-1 overflow-auto">
          <pre className="text-xs bg-black/40 border border-white/10 rounded p-3 max-h-[320px] overflow-auto">{system ? JSON.stringify(system, null, 2) : '(refresh to load)'}</pre>
          <div className="mt-4">
            <h3 className="text-sm font-bold tracking-[0.2em] text-gray-200">CAPABILITIES</h3>
            <pre className="mt-2 text-xs bg-black/40 border border-white/10 rounded p-3 max-h-[260px] overflow-auto">{caps ? JSON.stringify(caps, null, 2) : '(refresh to load)'}</pre>
          </div>
          <div className="mt-4">
            <h3 className="text-sm font-bold tracking-[0.2em] text-gray-200">UNIFICATION SCAN</h3>
            <pre className="mt-2 text-xs bg-black/40 border border-white/10 rounded p-3 max-h-[320px] overflow-auto">{unify ? JSON.stringify(unify, null, 2) : '(run Unify Scan to load)'}</pre>
          </div>
        </div>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SPARKET VIEW - The Ultimate Marketing Engine Dashboard
// ═══════════════════════════════════════════════════════════════════════════════

function SparketView({ data, onRefresh }) {
  const [loading, setLoading] = useState(false)
  
  // Default data if API not connected
  const field = data?.field || { state: 'nascent', coherence: 50, dominant_energy: 'quiet', emerging_themes: [] }
  const impact = data?.impact || { lives_touched: 0, transformations: 0, ripple_effects: 0 }
  const ripple = data?.ripple || { multiplication_ratio: 0, total_nodes: 0, multipliers: 0 }
  const tests = data?.tests || []
  const transmissions = data?.transmissions || []
  const marketing = data?.marketing || {}
  const sparketFunnel = marketing?.sparket || { visits_7d: 0, optins_7d: 0, visits_24h: 0, optins_24h: 0 }
  const whaletrackFunnel = marketing?.whaletrack || { landing_views_7d: 0, optins_7d: 0, go_live_started_7d: 0, uc_purchase_succeeded_7d: 0 }
  const revenue = marketing?.revenue || { uc_usd_30d: 0, uc_uc_30d: 0 }
  
  const handleRefresh = async () => {
    setLoading(true)
    await onRefresh()
    setLoading(false)
  }
  
  // Coherence ring color based on score
  const getCoherenceColor = (score) => {
    if (score >= 80) return '#22c55e' // green
    if (score >= 60) return '#eab308' // yellow
    if (score >= 40) return '#f97316' // orange
    return '#ef4444' // red
  }

  return (
    <div className="h-full flex flex-col gap-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold flex items-center gap-3">
          <Sparkles className="text-purple-400" /> 
          <span className="bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
            SPARKET ENGINE
          </span>
        </h2>
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-500">Transformation over Extraction</span>
          <button 
            onClick={handleRefresh} 
            className={`p-2 rounded-lg bg-white/5 hover:bg-white/10 transition ${loading ? 'animate-spin' : ''}`}
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-3 gap-6 flex-1">
        
        {/* Left Column: Field Coherence + Impact */}
        <div className="flex flex-col gap-6">
          {/* Field Coherence */}
          <div className="glass rounded-xl p-6 flex-1">
            <h3 className="font-bold text-purple-400 flex items-center gap-2 mb-4">
              <Radio size={16} /> FIELD COHERENCE
            </h3>
            
            <div className="flex items-center justify-center mb-6">
              {/* Coherence Ring */}
              <div className="relative w-32 h-32">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="64" cy="64" r="56"
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth="8"
                    fill="none"
                  />
                  <circle
                    cx="64" cy="64" r="56"
                    stroke={getCoherenceColor(field.coherence)}
                    strokeWidth="8"
                    fill="none"
                    strokeDasharray={`${field.coherence * 3.52} 352`}
                    className="transition-all duration-1000"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-3xl font-bold">{Math.round(field.coherence)}</span>
                  <span className="text-xs text-gray-500">COHERENCE</span>
                </div>
              </div>
            </div>
            
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-500">State</span>
                <span className={`text-sm font-bold capitalize ${
                  field.state === 'peak' ? 'text-green-400' :
                  field.state === 'coherent' ? 'text-blue-400' :
                  field.state === 'gathering' ? 'text-yellow-400' :
                  'text-gray-400'
                }`}>{field.state}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-gray-500">Energy</span>
                <span className="text-sm text-purple-300">{field.dominant_energy}</span>
              </div>
              {field.emerging_themes?.length > 0 && (
                <div>
                  <span className="text-xs text-gray-500">Emerging Themes</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {field.emerging_themes.slice(0, 3).map((theme, i) => (
                      <span key={i} className="text-[10px] bg-purple-500/20 text-purple-300 px-2 py-0.5 rounded">
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          
          {/* Impact Metrics */}
          <div className="glass rounded-xl p-6">
            <h3 className="font-bold text-green-400 flex items-center gap-2 mb-4">
              <Heart size={16} /> IMPACT
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400">{impact.lives_touched}</div>
                <div className="text-[10px] text-gray-500">Lives Touched</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-400">{impact.transformations}</div>
                <div className="text-[10px] text-gray-500">Transformations</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-400">{impact.ripple_effects}</div>
                <div className="text-[10px] text-gray-500">Ripples</div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Middle Column: Ripple Network + Transmissions */}
        <div className="flex flex-col gap-6">
          {/* Ripple Network */}
          <div className="glass rounded-xl p-6">
            <h3 className="font-bold text-blue-400 flex items-center gap-2 mb-4">
              <Waves size={16} /> RIPPLE NETWORK
            </h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Multiplication Ratio</span>
                <span className="text-xl font-bold text-blue-400">1:{ripple.multiplication_ratio?.toFixed(1) || '0'}</span>
              </div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all"
                  style={{ width: `${Math.min(ripple.multiplication_ratio * 33, 100)}%` }}
                />
              </div>
              <div className="grid grid-cols-2 gap-4 text-center">
                <div className="bg-white/5 p-3 rounded-lg">
                  <div className="text-lg font-bold">{ripple.total_nodes}</div>
                  <div className="text-[10px] text-gray-500">Total Nodes</div>
                </div>
                <div className="bg-white/5 p-3 rounded-lg">
                  <div className="text-lg font-bold text-green-400">{ripple.multipliers}</div>
                  <div className="text-[10px] text-gray-500">Multipliers</div>
                </div>
              </div>
            </div>
          </div>
          
          {/* Living Transmissions */}
          <div className="glass rounded-xl p-6 flex-1 overflow-hidden flex flex-col">
            <h3 className="font-bold text-yellow-400 flex items-center gap-2 mb-4">
              <Sparkles size={16} /> LIVING TRANSMISSIONS
            </h3>
            <div className="flex-1 overflow-y-auto space-y-3">
              {transmissions.length > 0 ? transmissions.slice(0, 5).map((tx, i) => (
                <div key={i} className="bg-white/5 p-3 rounded-lg border-l-2 border-yellow-500">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs text-yellow-400 capitalize">{tx.state}</span>
                    <span className="text-xs text-gray-500">Gen {tx.generation}</span>
                  </div>
                  <div className="text-sm text-gray-300 line-clamp-2">{tx.title || tx.current_form?.slice(0, 60)}</div>
                  <div className="flex gap-4 mt-2 text-[10px] text-gray-500">
                    <span>Resonance: {tx.resonance_score}%</span>
                    <span>Breakthroughs: {tx.breakthroughs_caused}</span>
                  </div>
                </div>
              )) : (
                <div className="text-center text-gray-500 py-8">
                  <Sparkles size={32} className="mx-auto mb-2 opacity-20" />
                  <div>No transmissions yet</div>
                  <div className="text-xs mt-1">Create content to see it here</div>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Right Column: Ad Tests + Budget */}
        <div className="flex flex-col gap-6">
          {/* Funnel Metrics */}
          <div className="glass rounded-xl p-6">
            <h3 className="font-bold text-pink-400 flex items-center gap-2 mb-4">
              <TrendingUp size={16} /> FUNNEL (SPARKET → WHALETRACK → UC)
            </h3>
            <div className="space-y-4">
              <div className="bg-white/5 p-3 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="text-xs text-gray-400">Sparket Movement (7d)</div>
                  <div className="text-xs text-gray-500">24h: {sparketFunnel.visits_24h} visits / {sparketFunnel.optins_24h} opt-ins</div>
                </div>
                <div className="mt-2 grid grid-cols-3 gap-2 text-center">
                  <div className="bg-black/20 p-2 rounded">
                    <div className="text-lg font-bold text-blue-300">{sparketFunnel.visits_7d}</div>
                    <div className="text-[10px] text-gray-500">Visits</div>
                  </div>
                  <div className="bg-black/20 p-2 rounded">
                    <div className="text-lg font-bold text-green-300">{sparketFunnel.optins_7d}</div>
                    <div className="text-[10px] text-gray-500">Opt-ins</div>
                  </div>
                  <div className="bg-black/20 p-2 rounded">
                    <div className="text-lg font-bold text-purple-300">
                      {sparketFunnel.visits_7d > 0 ? `${Math.round((sparketFunnel.optins_7d / sparketFunnel.visits_7d) * 100)}%` : '—'}
                    </div>
                    <div className="text-[10px] text-gray-500">Conv</div>
                  </div>
                </div>
              </div>

              <div className="bg-white/5 p-3 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="text-xs text-gray-400">WhaleTrack (7d)</div>
                  <a className="text-[10px] text-blue-400 hover:underline" href="/sparket/m/whaletrack" target="_blank" rel="noreferrer">Open funnel</a>
                </div>
                <div className="mt-2 grid grid-cols-4 gap-2 text-center">
                  <div className="bg-black/20 p-2 rounded">
                    <div className="text-lg font-bold text-blue-300">{whaletrackFunnel.landing_views_7d}</div>
                    <div className="text-[10px] text-gray-500">Views</div>
                  </div>
                  <div className="bg-black/20 p-2 rounded">
                    <div className="text-lg font-bold text-green-300">{whaletrackFunnel.optins_7d}</div>
                    <div className="text-[10px] text-gray-500">Opt-ins</div>
                  </div>
                  <div className="bg-black/20 p-2 rounded">
                    <div className="text-lg font-bold text-yellow-300">{whaletrackFunnel.go_live_started_7d}</div>
                    <div className="text-[10px] text-gray-500">Go Live</div>
                  </div>
                  <div className="bg-black/20 p-2 rounded">
                    <div className="text-lg font-bold text-pink-300">{whaletrackFunnel.uc_purchase_succeeded_7d}</div>
                    <div className="text-[10px] text-gray-500">UC Buys</div>
                  </div>
                </div>
                <div className="mt-2 text-[10px] text-gray-500">
                  UC (30d): ${Number(revenue.uc_usd_30d || 0).toLocaleString()} / {Number(revenue.uc_uc_30d || 0).toLocaleString()} UC
                </div>
              </div>
            </div>
          </div>

          {/* Active Tests */}
          <div className="glass rounded-xl p-6 flex-1 overflow-hidden flex flex-col">
            <h3 className="font-bold text-orange-400 flex items-center gap-2 mb-4">
              <Target size={16} /> AD TESTS
            </h3>
            <div className="flex-1 overflow-y-auto space-y-3">
              {tests.length > 0 ? tests.slice(0, 5).map((test, i) => (
                <div key={i} className={`p-3 rounded-lg border-l-2 ${
                  test.decision === 'scale' ? 'bg-green-500/10 border-green-500' :
                  test.decision === 'kill' ? 'bg-red-500/10 border-red-500' :
                  'bg-white/5 border-orange-500'
                }`}>
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-xs text-orange-400">{test.platform}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      test.status === 'scaling' ? 'bg-green-500/20 text-green-400' :
                      test.status === 'testing' ? 'bg-yellow-500/20 text-yellow-400' :
                      test.status === 'killed' ? 'bg-red-500/20 text-red-400' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>{test.status}</span>
                  </div>
                  <div className="text-sm text-gray-300">{test.name}</div>
                  <div className="flex gap-4 mt-2 text-[10px] text-gray-500">
                    <span>Variants: {test.variants}</span>
                    <span>Spent: ${test.spent?.toFixed(2)}</span>
                    {test.decision && <span className="capitalize">{test.decision}</span>}
                  </div>
                </div>
              )) : (
                <div className="text-center text-gray-500 py-8">
                  <Target size={32} className="mx-auto mb-2 opacity-20" />
                  <div>No active tests</div>
                  <div className="text-xs mt-1">Generate ads to start testing</div>
                </div>
              )}
            </div>
          </div>
          
          {/* Budget Status */}
          <div className="glass rounded-xl p-6">
            <h3 className="font-bold text-green-400 flex items-center gap-2 mb-4">
              <DollarSign size={16} /> AD BUDGET
            </h3>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-400">Monthly</span>
                  <span className="text-green-400">$0 / $1,000</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full bg-green-500 w-0 transition-all" />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-400">Daily</span>
                  <span className="text-blue-400">$0 / $50</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 w-0 transition-all" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs mt-4">
                <div className="bg-white/5 p-2 rounded text-center">
                  <div className="text-gray-500">Test Budget</div>
                  <div className="text-yellow-400">30%</div>
                </div>
                <div className="bg-white/5 p-2 rounded text-center">
                  <div className="text-gray-500">Scale Budget</div>
                  <div className="text-green-400">70%</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Bottom: Quick Stats Bar */}
      <div className="glass rounded-xl p-4 flex justify-around items-center">
        <div className="text-center">
          <div className="text-xs text-gray-500">PHILOSOPHY</div>
          <div className="text-sm text-purple-300">Serve, Don't Sell</div>
        </div>
        <div className="w-px h-8 bg-white/10" />
        <div className="text-center">
          <div className="text-xs text-gray-500">PRIMARY METRIC</div>
          <div className="text-sm text-green-300">Lives Touched</div>
        </div>
        <div className="w-px h-8 bg-white/10" />
        <div className="text-center">
          <div className="text-xs text-gray-500">STRATEGY</div>
          <div className="text-sm text-blue-300">Free → Test → Scale</div>
        </div>
        <div className="w-px h-8 bg-white/10" />
        <div className="text-center">
          <div className="text-xs text-gray-500">STATUS</div>
          <div className="text-sm text-yellow-300">Ready to Spark</div>
        </div>
      </div>
    </div>
  )
}

export default App

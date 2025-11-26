import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Brain, Zap, Inbox, MessageSquare, Activity, Terminal, Send, Check, X, Plus, DollarSign, TrendingUp, Shield
} from 'lucide-react'

// --- CONFIG ---
const API_URL = '/api'
const WS_URL = 'ws://localhost:3000/ws'

function App() {
  const [activeTab, setActiveTab] = useState('brain')
  const [stats, setStats] = useState({ intents: 0, claims: 0 })
  const [connected, setConnected] = useState(false)
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [chatMessages, setChatMessages] = useState([])
  const [inboxItems, setInboxItems] = useState([])
  const [boardData, setBoardData] = useState({ intent: [], building: [], deployed: [] })
  const [treasuryData, setTreasuryData] = useState(null)
  
  const ws = useRef(null)

  useEffect(() => {
    fetch(`${API_URL}/chat`).then(res => res.json()).then(setChatMessages)
    fetch(`${API_URL}/graph`).then(res => res.json()).then(setGraphData)
    fetch(`${API_URL}/inbox`).then(res => res.json()).then(setInboxItems)
    fetch(`${API_URL}/board`).then(res => res.json()).then(setBoardData)
    fetch(`${API_URL}/treasury`).then(res => res.json()).then(setTreasuryData)
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
          <NavIcon icon={Brain} label="Brain" active={activeTab === 'brain'} onClick={() => setActiveTab('brain')} />
          <NavIcon icon={Zap} label="Muscle" active={activeTab === 'muscle'} onClick={() => setActiveTab('muscle')} />
          <NavIcon icon={DollarSign} label="Treasury" active={activeTab === 'treasury'} onClick={() => setActiveTab('treasury')} />
          <NavIcon icon={Inbox} label="Inbox" active={activeTab === 'inbox'} onClick={() => setActiveTab('inbox')} />
          <NavIcon icon={MessageSquare} label="Chat" active={activeTab === 'chat'} onClick={() => setActiveTab('chat')} />
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
              {activeTab === 'brain' && <BrainView board={boardData} onCreate={createMission} />}
              {activeTab === 'muscle' && <SystemGraph data={graphData} />}
              {activeTab === 'treasury' && <TreasuryView data={treasuryData} />}
              {activeTab === 'inbox' && <InboxView items={inboxItems} />}
              {activeTab === 'chat' && <ChatView messages={chatMessages} onSend={sendMessage} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}

function NavIcon({ icon: Icon, label, active, onClick }) {
  return (
    <button onClick={onClick} className={`w-full h-14 flex flex-col items-center justify-center transition-all ${active ? 'border-l-2 border-purple-500 bg-white/5 text-purple-400' : 'text-gray-500 hover:text-gray-300'}`}>
      <Icon size={24} /> <span className="text-[10px] mt-1">{label}</span>
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

// ... (BrainView, SystemGraph, InboxView, ChatView from previous step remain here) ...
// I will paste them back to ensure full file integrity.

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

export default App

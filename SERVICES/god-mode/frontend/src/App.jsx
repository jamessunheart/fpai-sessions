import { useState, useEffect, useRef, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Brain, Zap, Inbox, MessageSquare, Activity, Terminal, Send, Check, X
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
  
  const ws = useRef(null)

  // --- INITIAL DATA FETCH ---
  useEffect(() => {
    fetch(`${API_URL}/chat`).then(res => res.json()).then(setChatMessages)
    fetch(`${API_URL}/graph`).then(res => res.json()).then(setGraphData)
    fetch(`${API_URL}/inbox`).then(res => res.json()).then(setInboxItems)
  }, [])

  // --- WEBSOCKET ---
  useEffect(() => {
    const connect = () => {
      ws.current = new WebSocket(WS_URL)
      
      ws.current.onopen = () => setConnected(true)
      ws.current.onclose = () => {
        setConnected(false)
        setTimeout(connect, 3000)
      }

      ws.current.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'stats_update') setStats(msg.data)
        if (msg.type === 'graph_update') setGraphData(msg.data)
        if (msg.type === 'chat_new') setChatMessages(prev => [...prev, msg.data])
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

  return (
    <div className="flex h-screen bg-god-bg text-white font-mono overflow-hidden">
      
      {/* SIDEBAR */}
      <nav className="w-20 border-r border-white/10 flex flex-col items-center py-6 space-y-8 z-50 glass">
        <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(147,51,234,0.5)]">
          <Terminal size={20} />
        </div>

        <div className="flex-1 flex flex-col space-y-4 w-full">
          <NavIcon icon={Brain} label="Brain" active={activeTab === 'brain'} onClick={() => setActiveTab('brain')} />
          <NavIcon icon={Zap} label="Muscle" active={activeTab === 'muscle'} onClick={() => setActiveTab('muscle')} />
          <NavIcon icon={Inbox} label="Inbox" active={activeTab === 'inbox'} onClick={() => setActiveTab('inbox')} />
          <NavIcon icon={MessageSquare} label="Chat" active={activeTab === 'chat'} onClick={() => setActiveTab('chat')} />
        </div>

        <div className={`w-3 h-3 rounded-full ${connected ? 'bg-green-500 shadow-[0_0_10px_#22c55e]' : 'bg-red-500 animate-pulse'}`} />
      </nav>

      {/* MAIN CONTENT */}
      <main className="flex-1 flex flex-col relative">
        <header className="h-16 border-b border-white/10 flex items-center justify-between px-8 glass z-40">
          <h1 className="text-xl font-bold tracking-[0.2em] text-purple-400">GOD MODE // THE COUNCIL</h1>
          <div className="flex gap-6 text-xs text-gray-400">
            <Stat label="ACTIVE INTENTS" value={stats.intents} />
            <Stat label="ACTIVE CLAIMS" value={stats.claims} />
            <Stat label="IMMUNITY" value="SECURE" color="text-green-400" />
          </div>
        </header>

        <div className="flex-1 p-8 overflow-y-auto relative bg-grid-pattern">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="h-full"
            >
              {activeTab === 'brain' && <BrainView />}
              {activeTab === 'muscle' && <SystemGraph data={graphData} />}
              {activeTab === 'inbox' && <InboxView items={inboxItems} />}
              {activeTab === 'chat' && <ChatView messages={chatMessages} onSend={sendMessage} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
    </div>
  )
}

// --- COMPONENTS ---

function NavIcon({ icon: Icon, label, active, onClick }) {
  return (
    <button 
      onClick={onClick}
      className={`w-full h-14 flex flex-col items-center justify-center transition-all duration-200 border-l-2 ${active ? 'border-purple-500 bg-white/5 text-purple-400' : 'border-transparent text-gray-500 hover:text-gray-300'}`}
    >
      <Icon size={24} />
      <span className="text-[10px] mt-1">{label}</span>
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

// --- VIEWS ---

function BrainView() {
  return (
    <div className="grid grid-cols-3 gap-6 h-full">
      <div className="glass rounded-lg p-4 flex flex-col">
        <h2 className="border-b border-white/10 pb-2 mb-4 flex items-center gap-2 text-purple-400 font-bold">
          <Brain size={16} /> STRATEGY
        </h2>
        <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">
          Kanban Board Coming Soon
        </div>
      </div>
    </div>
  )
}

// --- SYSTEM GRAPH (Native SVG Force Simulation) ---
function SystemGraph({ data }) {
  // Simple force simulation could go here, but for Phase 2 stability
  // we'll use a circular layout for agents and star layout for work
  // This avoids complex D3 math in raw React without a library
  
  const centerX = 400;
  const centerY = 300;
  const radius = 200;

  return (
    <div className="h-full glass rounded-lg overflow-hidden relative flex flex-col">
        <h2 className="absolute top-4 left-4 text-green-400 font-bold flex gap-2 z-10">
          <Activity size={16} /> LIVE MAP
        </h2>
        <svg className="w-full h-full">
            {/* Connections */}
            {data.links.map((link, i) => {
                // Mock positions for now - real force graph would be better with D3
                return (
                    <line key={i} x1={centerX} y1={centerY} x2={centerX + 100} y2={centerY + 100} stroke="rgba(255,255,255,0.1)" />
                )
            })}
            
            {/* Nodes */}
            {data.nodes.map((node, i) => {
                const angle = (i / data.nodes.length) * Math.PI * 2;
                const x = centerX + Math.cos(angle) * radius;
                const y = centerY + Math.sin(angle) * radius;
                
                return (
                    <g key={node.id} transform={`translate(${x}, ${y})`}>
                        <circle r="20" fill={node.group === 'core' ? '#9333ea' : '#22c55e'} className="animate-pulse" />
                        <text y="35" textAnchor="middle" fill="white" fontSize="10" className="opacity-70">{node.id}</text>
                    </g>
                )
            })}
            
            {/* Center Core */}
            <g transform={`translate(${centerX}, ${centerY})`}>
                <circle r="40" fill="#fff" opacity="0.1" />
                <text y="5" textAnchor="middle" fill="white" fontSize="12">CORE</text>
            </g>
        </svg>
        <div className="absolute bottom-4 right-4 text-xs text-gray-500">
            Nodes: {data.nodes.length} | Links: {data.links.length}
        </div>
    </div>
  )
}

// --- INBOX ---
function InboxView({ items }) {
  if (!items || items.length === 0) {
      return (
        <div className="flex justify-center items-center h-full">
           <div className="text-center">
              <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mb-6 mx-auto">
                 <Inbox size={40} className="text-blue-400" />
              </div>
              <h3 className="text-xl font-bold mb-2">All Clear</h3>
              <p className="text-gray-400 text-sm">Zero pending approvals.</p>
           </div>
        </div>
      )
  }

  return (
    <div className="flex flex-col items-center pt-10 space-y-6">
        <h2 className="text-2xl font-bold text-blue-400 tracking-widest">PENDING APPROVALS</h2>
        {items.map((item, i) => (
            <motion.div 
                key={i}
                initial={{ y: 50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                className="w-[600px] bg-god-card border border-white/10 rounded-xl p-6 shadow-2xl flex flex-col"
            >
                <div className="flex justify-between items-start mb-4">
                    <span className="text-xs text-blue-400 uppercase tracking-wider">{item.source}</span>
                    <span className="text-xs text-gray-500">{item.created_at}</span>
                </div>
                <p className="text-lg mb-8">{item.content}</p>
                <div className="flex gap-4">
                    <button className="flex-1 bg-green-600/20 hover:bg-green-600 text-green-400 hover:text-white py-3 rounded-lg font-bold border border-green-600/50 transition-all flex items-center justify-center gap-2">
                        <Check size={18} /> APPROVE
                    </button>
                    <button className="flex-1 bg-red-600/20 hover:bg-red-600 text-red-400 hover:text-white py-3 rounded-lg font-bold border border-red-600/50 transition-all flex items-center justify-center gap-2">
                        <X size={18} /> REJECT
                    </button>
                </div>
            </motion.div>
        ))}
    </div>
  )
}

// --- CHAT ---
function ChatView({ messages, onSend }) {
  const [input, setInput] = useState("")
  const scrollRef = useRef(null)

  useEffect(() => {
      if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages])

  const handleSend = (e) => {
      e.preventDefault()
      if(!input.trim()) return
      onSend(input)
      setInput("")
  }

  return (
    <div className="h-full flex flex-col glass rounded-lg overflow-hidden">
       <div className="flex-1 p-6 space-y-4 overflow-y-auto" ref={scrollRef}>
          <div className="text-center text-xs text-gray-500 py-4">--- ENCRYPTED CHANNEL ESTABLISHED ---</div>
          {messages.map((msg, i) => (
              <div key={i} className={`flex flex-col ${msg.sender === 'ARCHITECT' ? 'items-end' : 'items-start'}`}>
                  <div className="flex items-end gap-3 max-w-[80%]">
                      {msg.sender !== 'ARCHITECT' && (
                          <div className="w-8 h-8 rounded bg-purple-900 flex items-center justify-center text-xs shrink-0">
                              {msg.sender.substring(0,2).toUpperCase()}
                          </div>
                      )}
                      <div className={`p-3 rounded-xl text-sm ${msg.sender === 'ARCHITECT' ? 'bg-purple-600 text-white rounded-br-none' : 'bg-white/10 text-gray-200 rounded-bl-none'}`}>
                          {msg.content}
                      </div>
                  </div>
                  <span className="text-[10px] text-gray-600 mt-1 mx-12">{msg.sender} • {new Date(msg.timestamp).toLocaleTimeString()}</span>
              </div>
          ))}
       </div>
       <form onSubmit={handleSend} className="p-4 bg-black/20 border-t border-white/10">
          <div className="flex gap-2">
             <input 
                value={input}
                onChange={e => setInput(e.target.value)}
                type="text" 
                placeholder="Broadcast command to system..." 
                className="flex-1 bg-transparent border border-white/20 rounded px-4 py-3 text-sm focus:outline-none focus:border-purple-500 transition-colors bg-black/40" 
             />
             <button type="submit" className="bg-purple-600 hover:bg-purple-700 px-6 py-2 rounded text-sm font-bold flex items-center gap-2 transition-colors">
                 <Send size={16} /> SEND
             </button>
          </div>
       </form>
    </div>
  )
}

export default App

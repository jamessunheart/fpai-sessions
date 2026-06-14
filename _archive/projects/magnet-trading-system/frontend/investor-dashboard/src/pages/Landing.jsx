import React, { useState, useEffect } from 'react'
import axios from 'axios'
import PerformanceChart from '../components/PerformanceChart'
import { TrendingUp, Shield, Zap } from 'lucide-react'

function Landing() {
  const [performance, setPerformance] = useState(null)
  const [recentTrades, setRecentTrades] = useState([])

  useEffect(() => {
    // Fetch performance data
    axios.get('/api/performance/current')
      .then(res => setPerformance(res.data))
      .catch(err => console.error('Failed to fetch performance', err))

    // Fetch recent trades
    axios.get('/api/trades/recent?limit=5')
      .then(res => setRecentTrades(res.data))
      .catch(err => console.error('Failed to fetch trades', err))
  }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero Section */}
      <div className="text-center mb-16">
        <h1 className="text-5xl font-bold text-gray-900 mb-4">
          Magnet-Aware Trading Fund
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Algorithmic Trading with Survival Mathematics
        </p>

        {/* Performance Metrics */}
        {performance && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm text-gray-500">Equity</div>
              <div className="text-2xl font-bold">${performance.equity.toLocaleString()}</div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm text-gray-500">30-Day Return</div>
              <div className="text-2xl font-bold text-green-600">+{performance.return_30d}%</div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm text-gray-500">Max Drawdown</div>
              <div className="text-2xl font-bold">{performance.max_drawdown}%</div>
            </div>
            <div className="bg-white p-6 rounded-lg shadow">
              <div className="text-sm text-gray-500">Sharpe Ratio</div>
              <div className="text-2xl font-bold">{performance.sharpe_ratio}</div>
            </div>
          </div>
        )}
      </div>

      {/* Features */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
        <div className="bg-white p-8 rounded-lg shadow text-center">
          <Shield className="w-12 h-12 mx-auto mb-4 text-blue-600" />
          <h3 className="text-xl font-bold mb-2">Survival First</h3>
          <p className="text-gray-600">Circuit breaker at -2.5% protects your capital</p>
        </div>
        <div className="bg-white p-8 rounded-lg shadow text-center">
          <Zap className="w-12 h-12 mx-auto mb-4 text-yellow-600" />
          <h3 className="text-xl font-bold mb-2">Dynamic Leverage</h3>
          <p className="text-gray-600">Scales from 1.0x to 3.0x based on opportunity</p>
        </div>
        <div className="bg-white p-8 rounded-lg shadow text-center">
          <TrendingUp className="w-12 h-12 mx-auto mb-4 text-green-600" />
          <h3 className="text-xl font-bold mb-2">Magnet Detection</h3>
          <p className="text-gray-600">AI identifies high-probability price targets</p>
        </div>
      </div>

      {/* Equity Curve */}
      <div className="bg-white p-8 rounded-lg shadow mb-12">
        <h2 className="text-2xl font-bold mb-4">Live Equity Curve</h2>
        <PerformanceChart />
      </div>

      {/* Recent Trades */}
      <div className="bg-white p-8 rounded-lg shadow mb-12">
        <h2 className="text-2xl font-bold mb-4">Recent Trades</h2>
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2">Symbol</th>
              <th className="text-left py-2">Direction</th>
              <th className="text-left py-2">PnL</th>
              <th className="text-left py-2">Leverage</th>
            </tr>
          </thead>
          <tbody>
            {recentTrades.map((trade, i) => (
              <tr key={i} className="border-b">
                <td className="py-2">{trade.symbol}</td>
                <td className="py-2">{trade.direction}</td>
                <td className={`py-2 ${trade.pnl > 0 ? 'text-green-600' : 'text-red-600'}`}>
                  ${trade.pnl > 0 ? '+' : ''}{trade.pnl}
                </td>
                <td className="py-2">{trade.leverage}x</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* CTA */}
      <div className="text-center">
        <a href="/join" className="bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-bold hover:bg-blue-700">
          Join Fund
        </a>
      </div>
    </div>
  )
}

export default Landing

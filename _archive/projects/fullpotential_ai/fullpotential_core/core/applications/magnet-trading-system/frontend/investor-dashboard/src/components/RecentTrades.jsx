import React, { useState, useEffect } from 'react'
import axios from 'axios'

function RecentTrades() {
  const [trades, setTrades] = useState([])

  useEffect(() => {
    axios.get('/api/trades/recent?limit=10')
      .then(res => setTrades(res.data))
      .catch(err => console.error(err))
  }, [])

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <h3 className="text-xl font-bold mb-4">Recent Trades</h3>
      <table className="w-full">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2">Time</th>
            <th className="text-left py-2">Symbol</th>
            <th className="text-left py-2">Direction</th>
            <th className="text-left py-2">Entry</th>
            <th className="text-left py-2">Exit</th>
            <th className="text-left py-2">PnL</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((trade, i) => (
            <tr key={i} className="border-b">
              <td className="py-2 text-sm">{new Date(trade.timestamp).toLocaleString()}</td>
              <td className="py-2">{trade.symbol}</td>
              <td className="py-2">{trade.direction}</td>
              <td className="py-2">${trade.entry_price}</td>
              <td className="py-2">${trade.exit_price}</td>
              <td className={`py-2 ${trade.pnl > 0 ? 'text-green-600' : 'text-red-600'}`}>
                {trade.pnl > 0 ? '+' : ''}${trade.pnl}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default RecentTrades

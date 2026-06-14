import React, { useState, useEffect } from 'react'
import axios from 'axios'

function SystemStatus() {
  const [performance, setPerformance] = useState(null)
  const [fuseStatus, setFuseStatus] = useState(null)

  useEffect(() => {
    axios.get('/api/performance/current')
      .then(res => setPerformance(res.data))
      .catch(err => console.error(err))

    axios.get('/api/fuse/status')
      .then(res => setFuseStatus(res.data))
      .catch(err => console.error(err))
  }, [])

  if (!performance || !fuseStatus) {
    return <div>Loading...</div>
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div>
          <div className="text-sm text-gray-500">Leverage</div>
          <div className="text-2xl font-bold">{performance.leverage_used}x</div>
        </div>

        <div>
          <div className="text-sm text-gray-500">Fuse State</div>
          <div className={`text-2xl font-bold ${fuseStatus.armed ? 'text-green-600' : 'text-red-600'}`}>
            {fuseStatus.armed ? 'ARMED' : 'TRIGGERED'}
          </div>
        </div>

        <div>
          <div className="text-sm text-gray-500">Open Positions</div>
          <div className="text-2xl font-bold">{performance.open_positions}</div>
        </div>

        <div>
          <div className="text-sm text-gray-500">Daily PnL</div>
          <div className={`text-2xl font-bold ${performance.daily_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {performance.daily_pnl >= 0 ? '+' : ''}${performance.daily_pnl.toLocaleString()}
          </div>
        </div>
      </div>
    </div>
  )
}

export default SystemStatus

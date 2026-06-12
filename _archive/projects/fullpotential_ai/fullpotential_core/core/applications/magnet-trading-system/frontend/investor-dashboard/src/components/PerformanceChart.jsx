import React from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

function PerformanceChart() {
  // Mock data - replace with real API data
  const data = [
    { date: '2025-10-01', equity: 430000 },
    { date: '2025-10-08', equity: 432500 },
    { date: '2025-10-15', equity: 434200 },
    { date: '2025-10-22', equity: 435800 },
    { date: '2025-10-29', equity: 437240 },
  ]

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Line type="monotone" dataKey="equity" stroke="#2563eb" strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export default PerformanceChart

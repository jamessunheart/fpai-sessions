import React, { useState, useEffect } from 'react'
import axios from 'axios'
import PortfolioOverview from '../components/PortfolioOverview'
import SystemStatus from '../components/SystemStatus'
import PerformanceChart from '../components/PerformanceChart'

function Dashboard() {
  const [dashboardData, setDashboardData] = useState(null)

  useEffect(() => {
    // TODO: Add JWT authentication
    axios.get('/api/investor/dashboard')
      .then(res => setDashboardData(res.data))
      .catch(err => console.error('Failed to fetch dashboard', err))
  }, [])

  if (!dashboardData) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold mb-8">My Portfolio</h1>

      {/* Portfolio Overview */}
      <PortfolioOverview data={dashboardData} />

      {/* System Status */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold mb-4">System Status</h2>
        <SystemStatus />
      </div>

      {/* Performance Chart */}
      <div className="bg-white p-8 rounded-lg shadow mb-8">
        <h2 className="text-2xl font-bold mb-4">Performance Chart</h2>
        <PerformanceChart />
      </div>

      {/* Actions */}
      <div className="flex gap-4">
        <button className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700">
          Deposit More
        </button>
        <button className="bg-red-600 text-white px-6 py-3 rounded-lg hover:bg-red-700">
          Request Withdrawal
        </button>
      </div>
    </div>
  )
}

export default Dashboard

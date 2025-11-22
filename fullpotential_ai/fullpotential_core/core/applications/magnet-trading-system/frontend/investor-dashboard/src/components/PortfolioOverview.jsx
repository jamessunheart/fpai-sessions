import React from 'react'

function PortfolioOverview({ data }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
      <div className="bg-white p-6 rounded-lg shadow">
        <div className="text-sm text-gray-500">My Share</div>
        <div className="text-2xl font-bold">{data.share_percent}%</div>
        <div className="text-sm text-gray-500">${data.equity_value.toLocaleString()}</div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <div className="text-sm text-gray-500">My Returns</div>
        <div className="text-2xl font-bold text-green-600">+${data.total_return.toLocaleString()}</div>
        <div className="text-sm text-gray-500">+{data.return_percent}%</div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <div className="text-sm text-gray-500">Investment Date</div>
        <div className="text-xl font-bold">{data.investment_date}</div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <div className="text-sm text-gray-500">Status</div>
        <div className="text-xl font-bold text-green-600">Active</div>
      </div>
    </div>
  )
}

export default PortfolioOverview

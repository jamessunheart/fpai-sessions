import { useState } from 'react'
import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign,
  Target,
  Users,
  MousePointer
} from 'lucide-react'
import { useAnalyticsOverview, useDailyMetrics, useCampaignPerformance } from '../hooks/useApi'
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend
} from 'recharts'
import clsx from 'clsx'

export default function Analytics() {
  const [dateRange, setDateRange] = useState(30)
  
  const { data: overview, isLoading: overviewLoading } = useAnalyticsOverview(dateRange)
  const { data: dailyData, isLoading: dailyLoading } = useDailyMetrics(dateRange)
  const { data: campaignData } = useCampaignPerformance(dateRange)

  // Transform daily data for charts
  const chartData = dailyData?.metrics?.map((m: any) => ({
    date: new Date(m.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    spend: m.spend,
    revenue: m.revenue,
    profit: m.profit,
    conversions: m.conversions,
  })) || []

  const isLoading = overviewLoading || dailyLoading

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-display text-white">Analytics</h1>
          <p className="text-slate-400 mt-1">Deep dive into your advertising performance</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(parseInt(e.target.value))}
            className="input"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <MetricBox
          label="Total Spend"
          value={overview?.total_spend || 0}
          prefix="$"
          icon={DollarSign}
          loading={isLoading}
        />
        <MetricBox
          label="Total Revenue"
          value={overview?.total_revenue || 0}
          prefix="$"
          icon={TrendingUp}
          loading={isLoading}
          positive
        />
        <MetricBox
          label="Profit"
          value={(overview?.total_revenue || 0) - (overview?.total_spend || 0)}
          prefix="$"
          icon={(overview?.total_revenue || 0) >= (overview?.total_spend || 0) ? TrendingUp : TrendingDown}
          loading={isLoading}
          positive={(overview?.total_revenue || 0) >= (overview?.total_spend || 0)}
        />
        <MetricBox
          label="ROAS"
          value={overview?.overall_roas || 0}
          suffix="x"
          icon={Target}
          loading={isLoading}
          positive={(overview?.overall_roas || 0) >= 1}
        />
        <MetricBox
          label="Conversions"
          value={overview?.total_conversions || 0}
          icon={Users}
          loading={isLoading}
        />
        <MetricBox
          label="Active Campaigns"
          value={overview?.active_campaigns || 0}
          icon={MousePointer}
          loading={isLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue & Spend Chart */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Revenue vs Spend</h3>
          <div className="h-72">
            {isLoading ? (
              <div className="h-full flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorSpend" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis 
                    dataKey="date" 
                    stroke="#475569" 
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    stroke="#475569" 
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `$${value}`}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                  />
                  <Legend />
                  <Area 
                    type="monotone" 
                    dataKey="revenue" 
                    stroke="#10b981" 
                    fillOpacity={1} 
                    fill="url(#colorRevenue)" 
                    name="Revenue"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="spend" 
                    stroke="#6366f1" 
                    fillOpacity={1} 
                    fill="url(#colorSpend)" 
                    name="Spend"
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Profit Chart */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Daily Profit</h3>
          <div className="h-72">
            {isLoading ? (
              <div className="h-full flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <XAxis 
                    dataKey="date" 
                    stroke="#475569" 
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis 
                    stroke="#475569" 
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(value) => `$${value}`}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1e293b', 
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                  />
                  <Bar 
                    dataKey="profit" 
                    fill="#10b981"
                    radius={[4, 4, 0, 0]}
                    name="Profit"
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Campaign Performance Table */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Campaign Performance Breakdown</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-slate-400 text-sm border-b border-slate-800">
                <th className="pb-3 font-medium">Campaign</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium text-right">Impressions</th>
                <th className="pb-3 font-medium text-right">Clicks</th>
                <th className="pb-3 font-medium text-right">CTR</th>
                <th className="pb-3 font-medium text-right">Spend</th>
                <th className="pb-3 font-medium text-right">Revenue</th>
                <th className="pb-3 font-medium text-right">ROAS</th>
                <th className="pb-3 font-medium text-right">CPA</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {campaignData?.campaigns?.length ? (
                campaignData.campaigns.map((camp: any) => (
                  <tr key={camp.campaign_id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                    <td className="py-3">
                      <p className="text-white font-medium">{camp.campaign_name}</p>
                    </td>
                    <td className="py-3">
                      <span className={clsx('badge', `badge-${camp.status}`)}>
                        {camp.status}
                      </span>
                    </td>
                    <td className="py-3 text-right font-mono text-slate-300">
                      {(camp.impressions || 0).toLocaleString()}
                    </td>
                    <td className="py-3 text-right font-mono text-slate-300">
                      {(camp.clicks || 0).toLocaleString()}
                    </td>
                    <td className="py-3 text-right font-mono text-slate-300">
                      {(camp.ctr || 0).toFixed(2)}%
                    </td>
                    <td className="py-3 text-right font-mono text-slate-300">
                      ${(camp.spend || 0).toFixed(2)}
                    </td>
                    <td className="py-3 text-right font-mono text-emerald-400">
                      ${(camp.revenue || 0).toFixed(2)}
                    </td>
                    <td className={clsx(
                      'py-3 text-right font-mono font-medium',
                      (camp.roas || 0) >= 1 ? 'text-emerald-400' : 'text-red-400'
                    )}>
                      {(camp.roas || 0).toFixed(2)}x
                    </td>
                    <td className="py-3 text-right font-mono text-slate-300">
                      ${(camp.cpa || 0).toFixed(2)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={9} className="py-8 text-center text-slate-500">
                    No campaign data for selected period
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function MetricBox({ 
  label, 
  value, 
  prefix = '', 
  suffix = '',
  icon: Icon,
  loading,
  positive 
}: {
  label: string
  value: number
  prefix?: string
  suffix?: string
  icon: React.ElementType
  loading?: boolean
  positive?: boolean
}) {
  return (
    <div className="card p-4">
      {loading ? (
        <div className="animate-pulse">
          <div className="h-4 bg-slate-800 rounded w-20 mb-2"></div>
          <div className="h-6 bg-slate-800 rounded w-16"></div>
        </div>
      ) : (
        <>
          <div className="flex items-center gap-2 mb-2">
            <Icon className={clsx(
              'w-4 h-4',
              positive === undefined ? 'text-slate-400' : 
              positive ? 'text-emerald-400' : 'text-red-400'
            )} />
            <span className="text-xs text-slate-400">{label}</span>
          </div>
          <p className={clsx(
            'text-xl font-bold font-mono',
            positive === undefined ? 'text-white' :
            positive ? 'text-emerald-400' : 'text-red-400'
          )}>
            {prefix}{typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value}{suffix}
          </p>
        </>
      )}
    </div>
  )
}



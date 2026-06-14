import { 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Target, 
  Zap,
  ArrowUpRight,
  ArrowDownRight
} from 'lucide-react'
import { useAnalyticsOverview, useCampaignPerformance } from '../hooks/useApi'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import clsx from 'clsx'

function MetricCard({ 
  label, 
  value, 
  change, 
  icon: Icon, 
  prefix = '', 
  suffix = '',
  isPositive 
}: {
  label: string
  value: string | number
  change?: number
  icon: React.ElementType
  prefix?: string
  suffix?: string
  isPositive?: boolean
}) {
  const changeIsPositive = change !== undefined ? change >= 0 : isPositive

  return (
    <div className="card p-6 card-hover">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-slate-400 text-sm mb-1">{label}</p>
          <p className="text-2xl font-bold font-mono text-white">
            {prefix}{typeof value === 'number' ? value.toLocaleString() : value}{suffix}
          </p>
          {change !== undefined && (
            <div className={clsx(
              'flex items-center gap-1 mt-2 text-sm',
              changeIsPositive ? 'text-emerald-400' : 'text-red-400'
            )}>
              {changeIsPositive ? (
                <ArrowUpRight className="w-4 h-4" />
              ) : (
                <ArrowDownRight className="w-4 h-4" />
              )}
              <span>{Math.abs(change).toFixed(1)}%</span>
              <span className="text-slate-500">vs last period</span>
            </div>
          )}
        </div>
        <div className={clsx(
          'w-12 h-12 rounded-xl flex items-center justify-center',
          changeIsPositive !== false ? 'bg-emerald-500/10' : 'bg-red-500/10'
        )}>
          <Icon className={clsx(
            'w-6 h-6',
            changeIsPositive !== false ? 'text-emerald-400' : 'text-red-400'
          )} />
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data: overview, isLoading } = useAnalyticsOverview(30)
  const { data: campaignPerf } = useCampaignPerformance(30)

  // Mock data for demonstration
  const mockChartData = [
    { date: 'Jan 15', spend: 120, revenue: 280, profit: 160 },
    { date: 'Jan 16', spend: 150, revenue: 320, profit: 170 },
    { date: 'Jan 17', spend: 180, revenue: 450, profit: 270 },
    { date: 'Jan 18', spend: 200, revenue: 380, profit: 180 },
    { date: 'Jan 19', spend: 160, revenue: 520, profit: 360 },
    { date: 'Jan 20', spend: 190, revenue: 480, profit: 290 },
    { date: 'Jan 21', spend: 220, revenue: 620, profit: 400 },
  ]

  if (isLoading) {
    return (
      <div className="p-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-slate-800 rounded w-48"></div>
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-slate-800 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const profit = (overview?.total_revenue || 0) - (overview?.total_spend || 0)
  const isProfitable = profit >= 0

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold font-display text-white">Dashboard</h1>
        <p className="text-slate-400 mt-1">Your advertising performance at a glance</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Spend"
          value={(overview?.total_spend || 0).toFixed(2)}
          prefix="$"
          change={-5.2}
          icon={DollarSign}
          isPositive={false}
        />
        <MetricCard
          label="Total Revenue"
          value={(overview?.total_revenue || 0).toFixed(2)}
          prefix="$"
          change={12.5}
          icon={TrendingUp}
          isPositive={true}
        />
        <MetricCard
          label="Profit"
          value={Math.abs(profit).toFixed(2)}
          prefix={isProfitable ? '+$' : '-$'}
          change={isProfitable ? 8.3 : -8.3}
          icon={isProfitable ? TrendingUp : TrendingDown}
          isPositive={isProfitable}
        />
        <MetricCard
          label="ROAS"
          value={(overview?.overall_roas || 0).toFixed(2)}
          suffix="x"
          change={3.2}
          icon={Target}
          isPositive={(overview?.overall_roas || 0) >= 1}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue vs Spend Chart */}
        <div className="lg:col-span-2 card p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Revenue vs Spend</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={mockChartData}>
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
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis 
                  stroke="#475569" 
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => `$${value}`}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1e293b', 
                    border: '1px solid #334155',
                    borderRadius: '8px'
                  }}
                  labelStyle={{ color: '#94a3b8' }}
                />
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
          </div>
        </div>

        {/* Quick Stats */}
        <div className="card p-6 space-y-6">
          <h3 className="text-lg font-semibold text-white">Quick Stats</h3>
          
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Active Campaigns</span>
              <span className="text-white font-mono font-bold">{overview?.active_campaigns || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Conversions</span>
              <span className="text-white font-mono font-bold">{overview?.total_conversions || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Avg CPA</span>
              <span className="text-white font-mono font-bold">
                ${overview?.total_conversions ? ((overview?.total_spend || 0) / overview.total_conversions).toFixed(2) : '0.00'}
              </span>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-sm font-medium text-white">AI Recommendation</span>
            </div>
            <p className="text-sm text-slate-400">
              {(overview?.overall_roas || 0) >= 2 
                ? 'Campaign performing well! Consider scaling budget by 50%.'
                : 'Focus on improving ad creatives to boost CTR.'}
            </p>
          </div>
        </div>
      </div>

      {/* Campaign Performance Table */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Campaign Performance</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-slate-400 text-sm border-b border-slate-800">
                <th className="pb-3 font-medium">Campaign</th>
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium text-right">Spend</th>
                <th className="pb-3 font-medium text-right">Revenue</th>
                <th className="pb-3 font-medium text-right">Profit</th>
                <th className="pb-3 font-medium text-right">ROAS</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {campaignPerf?.campaigns?.length ? (
                campaignPerf.campaigns.map((camp: any) => (
                  <tr key={camp.campaign_id} className="border-b border-slate-800/50">
                    <td className="py-4">
                      <p className="text-white font-medium">{camp.campaign_name}</p>
                      <p className="text-slate-500 text-xs">{camp.offer_name}</p>
                    </td>
                    <td className="py-4">
                      <span className={clsx('badge', `badge-${camp.status}`)}>
                        {camp.status}
                      </span>
                    </td>
                    <td className="py-4 text-right font-mono text-slate-300">
                      ${camp.spend?.toFixed(2) || '0.00'}
                    </td>
                    <td className="py-4 text-right font-mono text-slate-300">
                      ${camp.revenue?.toFixed(2) || '0.00'}
                    </td>
                    <td className={clsx(
                      'py-4 text-right font-mono font-medium',
                      (camp.profit || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'
                    )}>
                      {(camp.profit || 0) >= 0 ? '+' : ''}${(camp.profit || 0).toFixed(2)}
                    </td>
                    <td className={clsx(
                      'py-4 text-right font-mono font-medium',
                      (camp.roas || 0) >= 1 ? 'text-emerald-400' : 'text-red-400'
                    )}>
                      {(camp.roas || 0).toFixed(2)}x
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500">
                    No campaigns yet. Create your first campaign to get started!
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



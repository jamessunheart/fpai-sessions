import { useState } from 'react'
import { 
  Plus, 
  Play, 
  Pause, 
  MoreVertical, 
  TrendingUp, 
  TrendingDown,
  Rocket,
  Clock
} from 'lucide-react'
import { useCampaigns, useOffers, useCreateCampaign, useLaunchCampaign, Campaign } from '../hooks/useApi'
import clsx from 'clsx'

function CreateCampaignModal({ 
  isOpen, 
  onClose, 
  onCreate,
  offers 
}: { 
  isOpen: boolean
  onClose: () => void
  onCreate: (campaign: Partial<Campaign>) => void
  offers: any[]
}) {
  const [formData, setFormData] = useState({
    name: '',
    offer_id: '',
    daily_budget: '',
    objective: 'OUTCOME_SALES',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onCreate({
      ...formData,
      daily_budget: parseFloat(formData.daily_budget),
    })
    setFormData({ name: '', offer_id: '', daily_budget: '', objective: 'OUTCOME_SALES' })
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h2 className="text-xl font-bold text-white mb-6">Create Campaign</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">Campaign Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input w-full"
              placeholder="e.g., Coaching Launch Q1"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Select Offer</label>
            <select
              value={formData.offer_id}
              onChange={(e) => setFormData({ ...formData, offer_id: e.target.value })}
              className="input w-full"
              required
            >
              <option value="">Choose an offer...</option>
              {offers?.map((offer: any) => (
                <option key={offer.id} value={offer.id}>
                  {offer.name} - ${offer.price}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Daily Budget (USD)</label>
            <input
              type="number"
              value={formData.daily_budget}
              onChange={(e) => setFormData({ ...formData, daily_budget: e.target.value })}
              className="input w-full"
              placeholder="50"
              min="5"
              step="1"
              required
            />
            <p className="text-xs text-slate-500 mt-1">Minimum $5/day recommended</p>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Objective</label>
            <select
              value={formData.objective}
              onChange={(e) => setFormData({ ...formData, objective: e.target.value })}
              className="input w-full"
            >
              <option value="OUTCOME_SALES">Conversions (Sales)</option>
              <option value="OUTCOME_LEADS">Lead Generation</option>
              <option value="OUTCOME_TRAFFIC">Website Traffic</option>
            </select>
          </div>

          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button type="submit" className="btn-primary flex-1">
              Create Campaign
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function CampaignCard({ 
  campaign,
  onLaunch 
}: { 
  campaign: Campaign
  onLaunch: () => void 
}) {
  const metrics = campaign.metrics
  const isProfitable = (metrics?.profit || 0) >= 0
  const roas = metrics?.roas || 0

  return (
    <div className="card p-6 card-hover">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-white text-lg">{campaign.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className={clsx('badge', `badge-${campaign.status}`)}>
              {campaign.status}
            </span>
            <span className="text-slate-500 text-xs">
              {campaign.days_running} days running
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {campaign.status === 'draft' && (
            <button 
              onClick={onLaunch}
              className="p-2 hover:bg-emerald-500/10 rounded-lg transition-colors group"
              title="Launch Campaign"
            >
              <Rocket className="w-4 h-4 text-slate-400 group-hover:text-emerald-400" />
            </button>
          )}
          {campaign.status === 'active' && (
            <button 
              className="p-2 hover:bg-amber-500/10 rounded-lg transition-colors group"
              title="Pause Campaign"
            >
              <Pause className="w-4 h-4 text-slate-400 group-hover:text-amber-400" />
            </button>
          )}
          {campaign.status === 'paused' && (
            <button 
              className="p-2 hover:bg-emerald-500/10 rounded-lg transition-colors group"
              title="Resume Campaign"
            >
              <Play className="w-4 h-4 text-slate-400 group-hover:text-emerald-400" />
            </button>
          )}
          <button className="p-2 hover:bg-slate-800 rounded-lg transition-colors">
            <MoreVertical className="w-4 h-4 text-slate-400" />
          </button>
        </div>
      </div>

      {/* Budget */}
      <div className="flex items-center gap-2 mb-4 text-sm">
        <Clock className="w-4 h-4 text-slate-500" />
        <span className="text-slate-400">Daily Budget:</span>
        <span className="text-white font-mono">${campaign.daily_budget}/day</span>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-slate-800/50 rounded-lg p-3">
          <p className="text-xs text-slate-500 mb-1">Spend</p>
          <p className="text-white font-mono font-bold">
            ${(metrics?.total_spend || 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-3">
          <p className="text-xs text-slate-500 mb-1">Revenue</p>
          <p className="text-white font-mono font-bold">
            ${(metrics?.total_revenue || 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-3">
          <p className="text-xs text-slate-500 mb-1">Profit</p>
          <p className={clsx(
            'font-mono font-bold',
            isProfitable ? 'text-emerald-400' : 'text-red-400'
          )}>
            {isProfitable ? '+' : ''}${(metrics?.profit || 0).toFixed(2)}
          </p>
        </div>
        <div className="bg-slate-800/50 rounded-lg p-3">
          <p className="text-xs text-slate-500 mb-1">ROAS</p>
          <p className={clsx(
            'font-mono font-bold flex items-center gap-1',
            roas >= 1 ? 'text-emerald-400' : 'text-red-400'
          )}>
            {roas >= 1 ? (
              <TrendingUp className="w-3 h-3" />
            ) : (
              <TrendingDown className="w-3 h-3" />
            )}
            {roas.toFixed(2)}x
          </p>
        </div>
      </div>

      {/* Footer */}
      <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
        <div className="text-sm">
          <span className="text-slate-500">Creatives: </span>
          <span className="text-white">{campaign.creative_count}</span>
        </div>
        <div className="text-sm">
          <span className="text-slate-500">Conversions: </span>
          <span className="text-white">{metrics?.total_conversions || 0}</span>
        </div>
      </div>
    </div>
  )
}

export default function Campaigns() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const { data: campaignsData, isLoading } = useCampaigns()
  const { data: offersData } = useOffers()
  const createCampaign = useCreateCampaign()
  const launchCampaign = useLaunchCampaign()

  const handleCreate = (campaign: Partial<Campaign>) => {
    createCampaign.mutate(campaign)
  }

  const handleLaunch = (campaignId: string) => {
    launchCampaign.mutate(campaignId)
  }

  const campaigns = campaignsData?.campaigns || []
  const offers = offersData?.offers || []

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-display text-white">Campaigns</h1>
          <p className="text-slate-400 mt-1">Manage your Meta advertising campaigns</p>
        </div>
        <button 
          onClick={() => setIsCreateModalOpen(true)}
          className="btn-primary flex items-center gap-2"
          disabled={offers.length === 0}
        >
          <Plus className="w-4 h-4" />
          New Campaign
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-slate-400 text-sm">Total Campaigns</p>
          <p className="text-2xl font-bold text-white">{campaigns.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-slate-400 text-sm">Active</p>
          <p className="text-2xl font-bold text-emerald-400">
            {campaigns.filter((c: Campaign) => c.status === 'active').length}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-slate-400 text-sm">Paused</p>
          <p className="text-2xl font-bold text-amber-400">
            {campaigns.filter((c: Campaign) => c.status === 'paused').length}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-slate-400 text-sm">Drafts</p>
          <p className="text-2xl font-bold text-slate-400">
            {campaigns.filter((c: Campaign) => c.status === 'draft').length}
          </p>
        </div>
      </div>

      {/* Campaigns Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-6 bg-slate-800 rounded w-3/4 mb-4"></div>
              <div className="h-4 bg-slate-800 rounded w-1/2 mb-4"></div>
              <div className="grid grid-cols-2 gap-3">
                {[1, 2, 3, 4].map((j) => (
                  <div key={j} className="h-16 bg-slate-800 rounded"></div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : campaigns.length ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {campaigns.map((campaign: Campaign) => (
            <CampaignCard 
              key={campaign.id} 
              campaign={campaign}
              onLaunch={() => handleLaunch(campaign.id)}
            />
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4">
            <Rocket className="w-8 h-8 text-slate-600" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">No campaigns yet</h3>
          <p className="text-slate-400 mb-6">
            {offers.length === 0 
              ? 'Create an offer first, then launch your campaign'
              : 'Create your first campaign to start advertising'}
          </p>
          <button 
            onClick={() => setIsCreateModalOpen(true)}
            className="btn-primary inline-flex items-center gap-2"
            disabled={offers.length === 0}
          >
            <Plus className="w-4 h-4" />
            Create Campaign
          </button>
        </div>
      )}

      {/* Create Modal */}
      <CreateCampaignModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreate}
        offers={offers}
      />
    </div>
  )
}



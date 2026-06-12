import { useState } from 'react'
import { Plus, ExternalLink, MoreVertical, DollarSign, Target } from 'lucide-react'
import { useOffers, useCreateOffer, Offer } from '../hooks/useApi'

function CreateOfferModal({ 
  isOpen, 
  onClose, 
  onCreate 
}: { 
  isOpen: boolean
  onClose: () => void
  onCreate: (offer: Partial<Offer>) => void 
}) {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    price: '',
    landing_url: '',
    offer_type: 'coaching',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onCreate({
      ...formData,
      price: parseFloat(formData.price),
    })
    setFormData({ name: '', description: '', price: '', landing_url: '', offer_type: 'coaching' })
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-slate-900 border border-slate-800 rounded-2xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h2 className="text-xl font-bold text-white mb-6">Create New Offer</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-2">Offer Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input w-full"
              placeholder="e.g., Business Coaching Package"
              required
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="input w-full h-24 resize-none"
              placeholder="What does this offer include?"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-2">Price (USD)</label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                className="input w-full"
                placeholder="997"
                min="0"
                step="0.01"
                required
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-2">Type</label>
              <select
                value={formData.offer_type}
                onChange={(e) => setFormData({ ...formData, offer_type: e.target.value })}
                className="input w-full"
              >
                <option value="coaching">Coaching</option>
                <option value="course">Course</option>
                <option value="service">Service</option>
                <option value="membership">Membership</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Landing Page URL</label>
            <input
              type="url"
              value={formData.landing_url}
              onChange={(e) => setFormData({ ...formData, landing_url: e.target.value })}
              className="input w-full"
              placeholder="https://fullpotential.ai/coaching"
              required
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose} className="btn-secondary flex-1">
              Cancel
            </button>
            <button type="submit" className="btn-primary flex-1">
              Create Offer
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function OfferCard({ offer }: { offer: Offer }) {
  return (
    <div className="card p-6 card-hover">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="font-semibold text-white text-lg">{offer.name}</h3>
          <span className="badge badge-active capitalize mt-1">{offer.offer_type}</span>
        </div>
        <button className="p-2 hover:bg-slate-800 rounded-lg transition-colors">
          <MoreVertical className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      {offer.description && (
        <p className="text-slate-400 text-sm mb-4 line-clamp-2">{offer.description}</p>
      )}

      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center">
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div>
            <p className="text-xs text-slate-500">Price</p>
            <p className="text-white font-mono font-bold">${offer.price.toLocaleString()}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
            <Target className="w-4 h-4 text-blue-400" />
          </div>
          <div>
            <p className="text-xs text-slate-500">Campaigns</p>
            <p className="text-white font-mono font-bold">{offer.campaign_count}</p>
          </div>
        </div>
      </div>

      <div className="pt-4 border-t border-slate-800 flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-500">Total Revenue</p>
          <p className="text-emerald-400 font-mono font-bold">${offer.total_revenue.toLocaleString()}</p>
        </div>
        <a 
          href={offer.landing_url} 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-sm text-slate-400 hover:text-white transition-colors"
        >
          <span>View Page</span>
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
    </div>
  )
}

export default function Offers() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const { data, isLoading } = useOffers()
  const createOffer = useCreateOffer()

  const handleCreate = (offer: Partial<Offer>) => {
    createOffer.mutate(offer)
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold font-display text-white">Offers</h1>
          <p className="text-slate-400 mt-1">Manage your coaching packages and products</p>
        </div>
        <button 
          onClick={() => setIsCreateModalOpen(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Offer
        </button>
      </div>

      {/* Offers Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-6 bg-slate-800 rounded w-3/4 mb-4"></div>
              <div className="h-4 bg-slate-800 rounded w-1/2 mb-4"></div>
              <div className="h-20 bg-slate-800 rounded"></div>
            </div>
          ))}
        </div>
      ) : data?.offers?.length ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {data.offers.map((offer) => (
            <OfferCard key={offer.id} offer={offer} />
          ))}
        </div>
      ) : (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4">
            <DollarSign className="w-8 h-8 text-slate-600" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">No offers yet</h3>
          <p className="text-slate-400 mb-6">Create your first coaching offer to start advertising</p>
          <button 
            onClick={() => setIsCreateModalOpen(true)}
            className="btn-primary inline-flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Your First Offer
          </button>
        </div>
      )}

      {/* Create Modal */}
      <CreateOfferModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={handleCreate}
      />
    </div>
  )
}



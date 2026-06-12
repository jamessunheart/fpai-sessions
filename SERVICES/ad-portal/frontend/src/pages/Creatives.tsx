import { useState } from 'react'
import { 
  Sparkles, 
  Image as ImageIcon, 
  FileText,
  Copy,
  Check
} from 'lucide-react'
import { useOffers, useGenerateCreatives } from '../hooks/useApi'

interface GeneratedCreative {
  variation: string
  headline: string
  primary_text: string
  description: string
  image_prompt: string
  reasoning?: string
}

export default function Creatives() {
  const [selectedOfferId, setSelectedOfferId] = useState('')
  const [tone, setTone] = useState('professional')
  const [numVariations, setNumVariations] = useState(3)
  const [generatedCreatives, setGeneratedCreatives] = useState<GeneratedCreative[]>([])
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const { data: offersData } = useOffers()
  const generateCreatives = useGenerateCreatives()

  const offers = offersData?.offers || []

  const handleGenerate = () => {
    if (!selectedOfferId) return

    generateCreatives.mutate({
      offer_id: selectedOfferId,
      tone,
      num_variations: numVariations,
    }, {
      onSuccess: (data) => {
        setGeneratedCreatives(data.creatives || [])
      }
    })
  }

  const copyToClipboard = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedId(id)
    setTimeout(() => setCopiedId(null), 2000)
  }

  return (
    <div className="p-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold font-display text-white">Creative Studio</h1>
        <p className="text-slate-400 mt-1">Generate AI-powered ad creatives for your campaigns</p>
      </div>

      {/* Generator Card */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-semibold text-white">AI Creative Generator</h2>
            <p className="text-sm text-slate-400">Generate multiple ad variations in seconds</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div>
            <label className="block text-sm text-slate-400 mb-2">Select Offer</label>
            <select
              value={selectedOfferId}
              onChange={(e) => setSelectedOfferId(e.target.value)}
              className="input w-full"
            >
              <option value="">Choose an offer...</option>
              {offers.map((offer: any) => (
                <option key={offer.id} value={offer.id}>
                  {offer.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Tone</label>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              className="input w-full"
            >
              <option value="professional">Professional</option>
              <option value="casual">Casual</option>
              <option value="urgent">Urgent</option>
              <option value="inspirational">Inspirational</option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-2">Variations</label>
            <select
              value={numVariations}
              onChange={(e) => setNumVariations(parseInt(e.target.value))}
              className="input w-full"
            >
              <option value={1}>1 variation</option>
              <option value={2}>2 variations</option>
              <option value={3}>3 variations</option>
              <option value={5}>5 variations</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleGenerate}
              disabled={!selectedOfferId || generateCreatives.isPending}
              className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {generateCreatives.isPending ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Generated Creatives */}
      {generatedCreatives.length > 0 && (
        <div className="space-y-6">
          <h2 className="text-xl font-semibold text-white">Generated Creatives</h2>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {generatedCreatives.map((creative, index) => (
              <div key={index} className="card p-6 card-hover">
                <div className="flex items-center justify-between mb-4">
                  <span className="badge bg-purple-500/20 text-purple-400">
                    Variation {creative.variation}
                  </span>
                </div>

                <div className="space-y-4">
                  {/* Headline */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs text-slate-500 uppercase tracking-wide">Headline</label>
                      <button
                        onClick={() => copyToClipboard(creative.headline, `headline-${index}`)}
                        className="p-1 hover:bg-slate-800 rounded transition-colors"
                      >
                        {copiedId === `headline-${index}` ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3 text-slate-500" />
                        )}
                      </button>
                    </div>
                    <p className="text-white font-medium">{creative.headline}</p>
                  </div>

                  {/* Primary Text */}
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="text-xs text-slate-500 uppercase tracking-wide">Primary Text</label>
                      <button
                        onClick={() => copyToClipboard(creative.primary_text, `primary-${index}`)}
                        className="p-1 hover:bg-slate-800 rounded transition-colors"
                      >
                        {copiedId === `primary-${index}` ? (
                          <Check className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <Copy className="w-3 h-3 text-slate-500" />
                        )}
                      </button>
                    </div>
                    <p className="text-slate-300 text-sm">{creative.primary_text}</p>
                  </div>

                  {/* Description */}
                  <div>
                    <label className="text-xs text-slate-500 uppercase tracking-wide block mb-1">Description</label>
                    <p className="text-slate-400 text-sm">{creative.description}</p>
                  </div>

                  {/* Image Prompt */}
                  <div className="pt-4 border-t border-slate-800">
                    <div className="flex items-center gap-2 mb-2">
                      <ImageIcon className="w-4 h-4 text-slate-500" />
                      <label className="text-xs text-slate-500 uppercase tracking-wide">Image Prompt</label>
                    </div>
                    <p className="text-slate-400 text-xs italic">{creative.image_prompt}</p>
                  </div>

                  {/* Reasoning */}
                  {creative.reasoning && (
                    <div className="pt-4 border-t border-slate-800">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="w-4 h-4 text-slate-500" />
                        <label className="text-xs text-slate-500 uppercase tracking-wide">AI Reasoning</label>
                      </div>
                      <p className="text-slate-500 text-xs">{creative.reasoning}</p>
                    </div>
                  )}
                </div>

                {/* Actions */}
                <div className="mt-4 pt-4 border-t border-slate-800">
                  <button className="btn-secondary w-full text-sm">
                    Add to Campaign
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {generatedCreatives.length === 0 && !generateCreatives.isPending && (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4">
            <Sparkles className="w-8 h-8 text-slate-600" />
          </div>
          <h3 className="text-xl font-semibold text-white mb-2">No creatives generated yet</h3>
          <p className="text-slate-400 mb-6">
            Select an offer and generate AI-powered ad variations
          </p>
        </div>
      )}
    </div>
  )
}



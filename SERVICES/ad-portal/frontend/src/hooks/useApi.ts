import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface Offer {
  id: string
  name: string
  description?: string
  price: number
  currency: string
  offer_type: string
  landing_url: string
  active: boolean
  created_at: string
  campaign_count: number
  total_revenue: number
}

export interface Campaign {
  id: string
  name: string
  offer_id: string
  status: string
  daily_budget: number
  meta_campaign_id?: string
  created_at: string
  days_running: number
  creative_count: number
  metrics?: {
    total_spend: number
    total_revenue: number
    profit: number
    roas: number
    total_conversions: number
  }
}

export interface Creative {
  id: string
  campaign_id: string
  headline: string
  primary_text: string
  description?: string
  variation: string
  active: boolean
  metrics?: {
    impressions: number
    clicks: number
    ctr: number
  }
}

export interface AnalyticsOverview {
  total_spend: number
  total_revenue: number
  total_profit: number
  total_conversions: number
  overall_roas: number
  active_campaigns: number
}

// Offers
export function useOffers() {
  return useQuery({
    queryKey: ['offers'],
    queryFn: async () => {
      const { data } = await api.get<{ offers: Offer[]; total: number }>('/offers')
      return data
    },
  })
}

export function useCreateOffer() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (offer: Partial<Offer>) => {
      const { data } = await api.post<Offer>('/offers', offer)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['offers'] })
    },
  })
}

// Campaigns
export function useCampaigns(offerId?: string) {
  return useQuery({
    queryKey: ['campaigns', offerId],
    queryFn: async () => {
      const params = offerId ? { offer_id: offerId } : {}
      const { data } = await api.get<{ campaigns: Campaign[]; total: number }>('/campaigns', { params })
      return data
    },
  })
}

export function useCreateCampaign() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (campaign: Partial<Campaign>) => {
      const { data } = await api.post<Campaign>('/campaigns', campaign)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    },
  })
}

export function useLaunchCampaign() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (campaignId: string) => {
      const { data } = await api.post(`/campaigns/${campaignId}/launch`)
      return data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
    },
  })
}

// Creatives
export function useCreatives(campaignId?: string) {
  return useQuery({
    queryKey: ['creatives', campaignId],
    queryFn: async () => {
      const params = campaignId ? { campaign_id: campaignId } : {}
      const { data } = await api.get<Creative[]>('/creatives', { params })
      return data
    },
    enabled: !!campaignId,
  })
}

export function useGenerateCreatives() {
  return useMutation({
    mutationFn: async (request: { offer_id: string; tone?: string; num_variations?: number }) => {
      const { data } = await api.post('/creatives/generate', request)
      return data
    },
  })
}

// Analytics
export function useAnalyticsOverview(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'overview', days],
    queryFn: async () => {
      const { data } = await api.get<AnalyticsOverview>('/analytics/overview', { params: { days } })
      return data
    },
  })
}

export function useDailyMetrics(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'daily', days],
    queryFn: async () => {
      const { data } = await api.get('/analytics/daily', { params: { days } })
      return data
    },
  })
}

export function useCampaignPerformance(days: number = 30) {
  return useQuery({
    queryKey: ['analytics', 'campaigns', days],
    queryFn: async () => {
      const { data } = await api.get('/analytics/campaigns', { params: { days } })
      return data
    },
  })
}



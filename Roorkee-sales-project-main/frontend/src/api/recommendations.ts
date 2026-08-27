import { apiClient } from './client'
import type { Recommendation } from './types'

export const getAllRecommendations = () =>
  apiClient.get<Recommendation[]>('/recommendations').then((res) => res.data)

export const getCustomerRecommendations = () =>
  apiClient.get<Recommendation[]>('/recommendations/customers').then((res) => res.data)

export const getRegionalRecommendations = () =>
  apiClient.get<Recommendation[]>('/recommendations/regions').then((res) => res.data)

export const getHighPriorityRecommendations = (limit = 20) =>
  apiClient
    .get<Recommendation[]>('/recommendations/high-priority', { params: { limit } })
    .then((res) => res.data)

export const getRiskRecommendations = () =>
  apiClient.get<Recommendation[]>('/recommendations/risk').then((res) => res.data)

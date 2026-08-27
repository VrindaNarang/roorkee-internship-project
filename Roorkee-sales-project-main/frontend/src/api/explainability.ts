import { apiClient } from './client'
import type { CustomerExplanation, GlobalExplanation, ModelSummaryResponse, TopFeaturesResponse } from './types'

export const getCustomerExplanation = (id: number | string) =>
  apiClient.get<CustomerExplanation>(`/explain/customer/${id}`).then((res) => res.data)

export const getGlobalExplanation = () =>
  apiClient.get<GlobalExplanation>('/explain/global').then((res) => res.data)

export const getTopFeatures = (model: 'purchase_probability' | 'expected_order_value' = 'purchase_probability', limit = 10) =>
  apiClient
    .get<TopFeaturesResponse>('/explain/top-features', { params: { model, limit } })
    .then((res) => res.data)

export const getModelSummary = () =>
  apiClient.get<ModelSummaryResponse>('/explain/model-summary').then((res) => res.data)

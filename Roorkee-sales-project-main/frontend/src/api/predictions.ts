import { apiClient } from './client'
import type { CustomerPrediction, RetrainResponse } from './types'

export interface PredictionListParams {
  state?: string
  institution_type?: string
  min_probability?: number
  min_expected_revenue?: number
}

export const getCustomerPredictions = (params: PredictionListParams = {}) =>
  apiClient.get<CustomerPrediction[]>('/predictions/customers', { params }).then((res) => res.data)

export const getCustomerPrediction = (id: number | string) =>
  apiClient.get<CustomerPrediction>(`/predictions/customer/${id}`).then((res) => res.data)

export const getHighProbabilityCustomers = (minProbability = 70, limit = 20) =>
  apiClient
    .get<CustomerPrediction[]>('/predictions/high-probability', {
      params: { min_probability: minProbability, limit },
    })
    .then((res) => res.data)

export const getTopOpportunities = (limit = 20) =>
  apiClient
    .get<CustomerPrediction[]>('/predictions/top-opportunities', { params: { limit } })
    .then((res) => res.data)

export const retrainModels = () => apiClient.post<RetrainResponse>('/ml/retrain').then((res) => res.data)

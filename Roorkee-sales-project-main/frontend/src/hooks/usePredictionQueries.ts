import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getCustomerPrediction,
  getCustomerPredictions,
  getHighProbabilityCustomers,
  getTopOpportunities,
  retrainModels,
} from '../api/predictions'
import type { PredictionListParams } from '../api/predictions'

export const useCustomerPredictions = (params: PredictionListParams) =>
  useQuery({
    queryKey: ['predictions', 'list', params],
    queryFn: () => getCustomerPredictions(params),
    placeholderData: (prev) => prev,
  })

export const useCustomerPrediction = (id: number | string | undefined) =>
  useQuery({
    queryKey: ['predictions', 'detail', id],
    queryFn: () => getCustomerPrediction(id as number | string),
    enabled: id !== undefined,
  })

export const useHighProbabilityCustomers = (minProbability = 70, limit = 20) =>
  useQuery({
    queryKey: ['predictions', 'high-probability', minProbability, limit],
    queryFn: () => getHighProbabilityCustomers(minProbability, limit),
  })

export const useTopOpportunities = (limit = 20) =>
  useQuery({ queryKey: ['predictions', 'top-opportunities', limit], queryFn: () => getTopOpportunities(limit) })

export const useRetrainModels = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: retrainModels,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions'] })
    },
  })
}

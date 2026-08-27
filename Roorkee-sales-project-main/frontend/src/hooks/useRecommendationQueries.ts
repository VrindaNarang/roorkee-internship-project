import { useQuery } from '@tanstack/react-query'
import {
  getAllRecommendations,
  getCustomerRecommendations,
  getHighPriorityRecommendations,
  getRegionalRecommendations,
  getRiskRecommendations,
} from '../api/recommendations'

export const useAllRecommendations = () =>
  useQuery({ queryKey: ['recommendations', 'all'], queryFn: getAllRecommendations })

export const useCustomerRecommendations = () =>
  useQuery({ queryKey: ['recommendations', 'customers'], queryFn: getCustomerRecommendations })

export const useRegionalRecommendations = () =>
  useQuery({ queryKey: ['recommendations', 'regions'], queryFn: getRegionalRecommendations })

export const useHighPriorityRecommendations = (limit = 20) =>
  useQuery({
    queryKey: ['recommendations', 'high-priority', limit],
    queryFn: () => getHighPriorityRecommendations(limit),
  })

export const useRiskRecommendations = () =>
  useQuery({ queryKey: ['recommendations', 'risk'], queryFn: getRiskRecommendations })

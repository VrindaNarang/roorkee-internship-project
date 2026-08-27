import { useQuery } from '@tanstack/react-query'
import {
  getAnalyticsRevenueByState,
  getAnalyticsSalesTrend,
  getCustomerInsights,
  getRegionPerformance,
} from '../api/analytics'

export const useAnalyticsSalesTrend = (months = 12) =>
  useQuery({
    queryKey: ['analytics', 'sales-trend', months],
    queryFn: () => getAnalyticsSalesTrend(months),
  })

export const useAnalyticsRevenueByState = () =>
  useQuery({ queryKey: ['analytics', 'revenue-by-state'], queryFn: getAnalyticsRevenueByState })

export const useRegionPerformance = () =>
  useQuery({ queryKey: ['analytics', 'region-performance'], queryFn: getRegionPerformance })

export const useCustomerInsights = () =>
  useQuery({ queryKey: ['analytics', 'customer-insights'], queryFn: getCustomerInsights })

import { apiClient } from './client'
import type { CustomerInsights, RegionPerformance, RevenueByState, SalesTrendPoint } from './types'

export const getAnalyticsSalesTrend = (months = 12) =>
  apiClient.get<SalesTrendPoint[]>('/analytics/sales-trend', { params: { months } }).then((res) => res.data)

export const getAnalyticsRevenueByState = () =>
  apiClient.get<RevenueByState[]>('/analytics/revenue-by-state').then((res) => res.data)

export const getRegionPerformance = () =>
  apiClient.get<RegionPerformance[]>('/analytics/region-performance').then((res) => res.data)

export const getCustomerInsights = () =>
  apiClient.get<CustomerInsights>('/analytics/customer-insights').then((res) => res.data)

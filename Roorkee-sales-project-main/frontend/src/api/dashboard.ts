import { apiClient } from './client'
import type {
  CategoryDistribution,
  DashboardSummary,
  RecentOrder,
  RevenueByState,
  SalesTrendPoint,
  TopCustomer,
  TopProduct,
} from './types'

export const getDashboardSummary = () =>
  apiClient.get<DashboardSummary>('/dashboard/summary').then((res) => res.data)

export const getSalesTrend = (months = 12) =>
  apiClient.get<SalesTrendPoint[]>('/dashboard/sales-trend', { params: { months } }).then((res) => res.data)

export const getRevenueByState = () =>
  apiClient.get<RevenueByState[]>('/dashboard/revenue-by-state').then((res) => res.data)

export const getCategoryDistribution = () =>
  apiClient.get<CategoryDistribution[]>('/dashboard/category-distribution').then((res) => res.data)

export const getTopCustomers = (limit = 10) =>
  apiClient.get<TopCustomer[]>('/dashboard/top-customers', { params: { limit } }).then((res) => res.data)

export const getTopProducts = (limit = 10) =>
  apiClient.get<TopProduct[]>('/dashboard/top-products', { params: { limit } }).then((res) => res.data)

export const getRecentOrders = (limit = 10) =>
  apiClient.get<RecentOrder[]>('/dashboard/recent-orders', { params: { limit } }).then((res) => res.data)

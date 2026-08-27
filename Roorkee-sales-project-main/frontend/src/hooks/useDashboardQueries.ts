import { useQuery } from '@tanstack/react-query'
import {
  getCategoryDistribution,
  getDashboardSummary,
  getRecentOrders,
  getRevenueByState,
  getSalesTrend,
  getTopCustomers,
  getTopProducts,
} from '../api/dashboard'

export const useDashboardSummary = () =>
  useQuery({ queryKey: ['dashboard', 'summary'], queryFn: getDashboardSummary })

export const useSalesTrend = (months = 12) =>
  useQuery({ queryKey: ['dashboard', 'sales-trend', months], queryFn: () => getSalesTrend(months) })

export const useRevenueByState = () =>
  useQuery({ queryKey: ['dashboard', 'revenue-by-state'], queryFn: getRevenueByState })

export const useCategoryDistribution = () =>
  useQuery({ queryKey: ['dashboard', 'category-distribution'], queryFn: getCategoryDistribution })

export const useTopCustomers = (limit = 10) =>
  useQuery({ queryKey: ['dashboard', 'top-customers', limit], queryFn: () => getTopCustomers(limit) })

export const useTopProducts = (limit = 10) =>
  useQuery({ queryKey: ['dashboard', 'top-products', limit], queryFn: () => getTopProducts(limit) })

export const useRecentOrders = (limit = 10) =>
  useQuery({ queryKey: ['dashboard', 'recent-orders', limit], queryFn: () => getRecentOrders(limit) })

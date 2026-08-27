import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getAtRiskCustomers,
  getCriticalCustomers,
  getCustomer,
  getCustomerHealth,
  getCustomerHealthList,
  getCustomerOrders,
  getCustomers,
  getCustomerStates,
  getHealthyCustomers,
  recalculateCustomerHealth,
} from '../api/customers'
import type { CustomerListParams } from '../api/customers'

export const useCustomers = (params: CustomerListParams) =>
  useQuery({
    queryKey: ['customers', 'list', params],
    queryFn: () => getCustomers(params),
    placeholderData: (prev) => prev,
  })

export const useCustomerStates = () =>
  useQuery({ queryKey: ['customers', 'states'], queryFn: getCustomerStates, staleTime: Infinity })

export const useCustomer = (id: number | string | undefined) =>
  useQuery({
    queryKey: ['customers', 'detail', id],
    queryFn: () => getCustomer(id as number | string),
    enabled: id !== undefined,
  })

export const useCustomerOrders = (id: number | string | undefined) =>
  useQuery({
    queryKey: ['customers', 'orders', id],
    queryFn: () => getCustomerOrders(id as number | string),
    enabled: id !== undefined,
  })

export const useCustomerHealthList = () =>
  useQuery({ queryKey: ['customers', 'health', 'list'], queryFn: getCustomerHealthList })

export const useCustomerHealth = (id: number | string | undefined) =>
  useQuery({
    queryKey: ['customers', 'health', 'detail', id],
    queryFn: () => getCustomerHealth(id as number | string),
    enabled: id !== undefined,
  })

export const useCriticalCustomers = (limit = 20) =>
  useQuery({ queryKey: ['customers', 'health', 'critical', limit], queryFn: () => getCriticalCustomers(limit) })

export const useHealthyCustomers = (limit = 20) =>
  useQuery({ queryKey: ['customers', 'health', 'healthy', limit], queryFn: () => getHealthyCustomers(limit) })

export const useAtRiskCustomers = (limit = 20) =>
  useQuery({ queryKey: ['customers', 'health', 'at-risk', limit], queryFn: () => getAtRiskCustomers(limit) })

export const useRecalculateHealth = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: recalculateCustomerHealth,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers', 'health'] })
    },
  })
}

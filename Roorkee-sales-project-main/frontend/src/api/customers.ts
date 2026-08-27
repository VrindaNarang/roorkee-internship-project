import { apiClient } from './client'
import type {
  CustomerDetail,
  CustomerHealthDetail,
  CustomerHealthListItem,
  CustomerListResponse,
  CustomerOrderItem,
  RecalculateHealthResponse,
} from './types'

export interface CustomerListParams {
  search?: string
  state?: string
  institution_type?: string
  status?: string
  page?: number
  page_size?: number
}

export const getCustomers = (params: CustomerListParams = {}) =>
  apiClient.get<CustomerListResponse>('/customers', { params }).then((res) => res.data)

export const getCustomerStates = () =>
  apiClient.get<string[]>('/customers/states').then((res) => res.data)

export const getCustomer = (id: number | string) =>
  apiClient.get<CustomerDetail>(`/customers/${id}`).then((res) => res.data)

export const getCustomerOrders = (id: number | string) =>
  apiClient.get<CustomerOrderItem[]>(`/customers/${id}/orders`).then((res) => res.data)

export const getCustomerHealthList = () =>
  apiClient.get<CustomerHealthListItem[]>('/customers/health').then((res) => res.data)

export const getCustomerHealth = (id: number | string) =>
  apiClient.get<CustomerHealthDetail>(`/customers/${id}/health`).then((res) => res.data)

export const getCriticalCustomers = (limit = 20) =>
  apiClient
    .get<CustomerHealthListItem[]>('/customers/critical', { params: { limit } })
    .then((res) => res.data)

export const getHealthyCustomers = (limit = 20) =>
  apiClient
    .get<CustomerHealthListItem[]>('/customers/healthy', { params: { limit } })
    .then((res) => res.data)

export const getAtRiskCustomers = (limit = 20) =>
  apiClient
    .get<CustomerHealthListItem[]>('/customers/at-risk', { params: { limit } })
    .then((res) => res.data)

export const recalculateCustomerHealth = () =>
  apiClient.post<RecalculateHealthResponse>('/customers/health').then((res) => res.data)

import { apiClient } from './client'
import type {
  ProductCategoryOut,
  ProductDetail,
  ProductListResponse,
  ProductSalesTrendPoint,
} from './types'

export interface ProductListParams {
  search?: string
  category?: string
  is_active?: boolean
  page?: number
  page_size?: number
}

export const getProducts = (params: ProductListParams = {}) =>
  apiClient.get<ProductListResponse>('/products', { params }).then((res) => res.data)

export const getProductCategories = () =>
  apiClient.get<ProductCategoryOut[]>('/products/categories').then((res) => res.data)

export const getProduct = (id: number | string) =>
  apiClient.get<ProductDetail>(`/products/${id}`).then((res) => res.data)

export const getProductSalesTrend = (id: number | string, months = 12) =>
  apiClient
    .get<ProductSalesTrendPoint[]>(`/products/${id}/sales-trend`, { params: { months } })
    .then((res) => res.data)

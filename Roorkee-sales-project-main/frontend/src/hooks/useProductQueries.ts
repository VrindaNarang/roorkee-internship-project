import { useQuery } from '@tanstack/react-query'
import {
  getProduct,
  getProductCategories,
  getProducts,
  getProductSalesTrend,
} from '../api/products'
import type { ProductListParams } from '../api/products'

export const useProducts = (params: ProductListParams) =>
  useQuery({
    queryKey: ['products', 'list', params],
    queryFn: () => getProducts(params),
    placeholderData: (prev) => prev,
  })

export const useProductCategories = () =>
  useQuery({ queryKey: ['products', 'categories'], queryFn: getProductCategories, staleTime: Infinity })

export const useProduct = (id: number | string | undefined) =>
  useQuery({
    queryKey: ['products', 'detail', id],
    queryFn: () => getProduct(id as number | string),
    enabled: id !== undefined,
  })

export const useProductSalesTrend = (id: number | string | undefined, months = 12) =>
  useQuery({
    queryKey: ['products', 'sales-trend', id, months],
    queryFn: () => getProductSalesTrend(id as number | string, months),
    enabled: id !== undefined,
  })

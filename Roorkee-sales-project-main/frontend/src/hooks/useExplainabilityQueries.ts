import { useQuery } from '@tanstack/react-query'
import { getCustomerExplanation, getGlobalExplanation, getModelSummary, getTopFeatures } from '../api/explainability'

export const useCustomerExplanation = (id: number | string | undefined) =>
  useQuery({
    queryKey: ['explain', 'customer', id],
    queryFn: () => getCustomerExplanation(id as number | string),
    enabled: id !== undefined,
  })

export const useGlobalExplanation = () =>
  useQuery({ queryKey: ['explain', 'global'], queryFn: getGlobalExplanation })

export const useTopFeatures = (model: 'purchase_probability' | 'expected_order_value' = 'purchase_probability', limit = 10) =>
  useQuery({ queryKey: ['explain', 'top-features', model, limit], queryFn: () => getTopFeatures(model, limit) })

export const useModelSummary = () =>
  useQuery({ queryKey: ['explain', 'model-summary'], queryFn: getModelSummary })

// Types mirror the backend Pydantic schemas 1:1 (see backend/app/schemas/*.py).

export interface DashboardSummary {
  total_revenue: number
  monthly_revenue: number
  total_orders: number
  active_customers: number
  average_order_value: number
  revenue_growth_pct: number
  currency: string
}

export interface SalesTrendPoint {
  month: string
  revenue: number
  orders: number
}

export interface RevenueByState {
  state: string
  region: string
  revenue: number
  orders: number
}

export interface CategoryDistribution {
  category: string
  revenue: number
  order_count: number
  pct_of_revenue: number
}

export interface TopCustomer {
  id: number
  name: string
  institution_type: InstitutionType
  state: string
  total_revenue: number
  total_orders: number
  last_order_date: string | null
}

export interface TopProduct {
  id: number
  sku: string
  name: string
  category: string
  total_revenue: number
  total_quantity: number
}

export interface RecentOrder {
  id: number
  order_number: string
  college_name: string
  order_date: string
  status: OrderStatus
  payment_status: PaymentStatus
  total_amount: number
}

export type InstitutionType = 'government' | 'private'
export type CollegeStatus = 'active' | 'dormant'
export type OrderStatus = 'pending' | 'fulfilled' | 'cancelled'
export type PaymentStatus = 'paid' | 'pending' | 'overdue'

export interface PaginationMeta {
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface CustomerListItem {
  id: number
  name: string
  institution_type: InstitutionType
  region: string
  state: string
  city: string
  status: CollegeStatus
  total_orders: number
  total_revenue: number
  last_order_date: string | null
}

export interface CustomerListResponse {
  items: CustomerListItem[]
  meta: PaginationMeta
}

export interface CustomerDetail {
  id: number
  name: string
  institution_type: InstitutionType
  region: string
  state: string
  city: string
  address: string
  contact_name: string
  contact_email: string
  contact_phone: string
  onboarded_date: string
  status: CollegeStatus
  total_orders: number
  total_revenue: number
  average_order_value: number
  last_order_date: string | null
}

export interface CustomerOrderItem {
  id: number
  order_number: string
  order_date: string
  status: OrderStatus
  payment_status: PaymentStatus
  total_amount: number
  item_count: number
}

export interface ProductListItem {
  id: number
  sku: string
  name: string
  category: string
  unit_price: number
  is_active: boolean
  total_revenue: number
  total_quantity_sold: number
}

export interface ProductListResponse {
  items: ProductListItem[]
  meta: PaginationMeta
}

export interface ProductDetail {
  id: number
  sku: string
  name: string
  category: string
  unit_price: number
  cost_price: number
  unit_of_measure: string
  is_active: boolean
  created_at: string
  total_revenue: number
  total_quantity_sold: number
  total_orders: number
}

export interface ProductSalesTrendPoint {
  month: string
  revenue: number
  quantity: number
}

export interface ProductCategoryOut {
  id: number
  name: string
}

export interface InstitutionTypeBreakdown {
  institution_type: InstitutionType
  customer_count: number
  revenue: number
  avg_order_value: number
}

export interface RegionPerformance {
  region: string
  revenue: number
  orders: number
  customer_count: number
  avg_order_value: number
}

export interface CustomerInsights {
  institution_type_breakdown: InstitutionTypeBreakdown[]
  new_customers_last_90_days: number
  at_risk_customers: number
  repeat_customer_pct: number
}

export type HealthStatus = 'healthy' | 'at_risk' | 'critical'
export type HealthTrend = 'improving' | 'declining' | 'stable' | 'new'

export interface CustomerHealthListItem {
  college_id: number
  name: string
  institution_type: InstitutionType
  region: string
  state: string
  health_score: number
  health_status: HealthStatus
  previous_health_score: number | null
  health_trend: HealthTrend
  last_updated: string
}

export interface ComponentScoreOut {
  raw_value: number
  normalized_score: number
  weight: number
  contribution: number
}

export interface CustomerHealthDetail extends CustomerHealthListItem {
  rfm_recency: number
  rfm_frequency: number
  rfm_monetary: number
  model_version: string
  component_breakdown: Record<string, ComponentScoreOut>
}

export interface RecalculateHealthResponse {
  scored_at: string
  total_customers: number
  healthy: number
  at_risk: number
  critical: number
  model_version: string
}

export interface FeatureContribution {
  feature: string
  value: number
  direction: 'increases' | 'decreases'
}

export interface CustomerPrediction {
  college_id: number
  name: string
  institution_type: InstitutionType
  region: string
  state: string
  purchase_probability: number // 0-100
  expected_order_value: number
  expected_revenue: number
  confidence_score: number // 0-100
  prediction_date: string
  model_version: string
  probability_explanation: FeatureContribution[]
  expected_value_explanation: FeatureContribution[]
}

export interface RetrainResponse {
  status: string
  version: string | null
  classifier_metrics: Record<string, unknown> | null
  regressor_metrics: Record<string, unknown> | null
  predictions_written: number | null
  message: string
}

export interface ModelExplanation {
  value: number
  positive_contributors: FeatureContribution[]
  negative_contributors: FeatureContribution[]
  reasons: string[]
  confidence: number | null
  plot_urls: Record<string, string>
}

export interface CustomerExplanation {
  college_id: number
  name: string
  health_score: ModelExplanation | null
  purchase_probability: ModelExplanation | null
  expected_order_value: ModelExplanation | null
  overall_confidence: number | null
  generated_at: string | null
}

export interface GlobalFeatureRow {
  feature: string
  mean_abs_contribution: number
  rank: number
}

export interface GlobalModelExplanation {
  top_features: GlobalFeatureRow[]
  summary_text: string
  plot_urls: Record<string, string>
}

export interface GlobalExplanation {
  generated_at: string
  model_version: string
  purchase_probability: GlobalModelExplanation
  expected_order_value: GlobalModelExplanation
}

export interface TopFeaturesResponse {
  model: string
  top_features: GlobalFeatureRow[]
}

export interface ModelSummaryEntry {
  model_name: string
  model_type: string
  version: string
  trained_at: string
  metrics: Record<string, unknown>
}

export interface ModelSummaryResponse {
  purchase_propensity_classifier: ModelSummaryEntry | null
  expected_order_value_regressor: ModelSummaryEntry | null
  customer_health_score: {
    model_version: string
    model_type: string
    note: string
    weights: Record<string, number>
  }
}

export type RecommendationType = 'customer' | 'risk' | 'regional' | 'sales'
export type RecommendationPriority = 'high' | 'medium' | 'low'

export interface Recommendation {
  rule_id: string
  recommendation_type: RecommendationType
  priority: RecommendationPriority
  priority_score: number // 0-100, for ranking within and across types
  title: string
  reason: string
  college_id: number | null
  college_name: string | null
  region: string | null
  metrics: Record<string, number>
}

export type UserRole = 'admin' | 'sales_manager' | 'sales_executive'

export interface LoginResponse {
  access_token: string
  token_type: string
  role: UserRole
  full_name: string
}

export interface CurrentUser {
  id: number
  email: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

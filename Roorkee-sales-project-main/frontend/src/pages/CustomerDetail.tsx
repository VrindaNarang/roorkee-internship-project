import { useState } from 'react'
import { Box, Chip, Skeleton, Stack, Tab, Tabs, Typography } from '@mui/material'
import EmailOutlinedIcon from '@mui/icons-material/EmailOutlined'
import PhoneOutlinedIcon from '@mui/icons-material/PhoneOutlined'
import PlaceOutlinedIcon from '@mui/icons-material/PlaceOutlined'
import { useNavigate, useParams } from 'react-router-dom'
import { KpiCard } from '../components/dashboard/KpiCard'
import { DataTable } from '../components/table/DataTable'
import { StatusChip } from '../components/common/StatusChip'
import { ErrorState } from '../components/common/ErrorState'
import { SectionCard } from '../components/common/SectionCard'
import { DetailHeader } from '../components/common/DetailHeader'
import { HealthScoreBar } from '../components/health/HealthScoreBar'
import { HealthTrendIndicator } from '../components/health/HealthTrendIndicator'
import { ProbabilityBar } from '../components/predictions/ProbabilityBar'
import { useCustomer, useCustomerHealth, useCustomerOrders } from '../hooks/useCustomerQueries'
import { useCustomerPrediction } from '../hooks/usePredictionQueries'
import { useCustomerExplanation } from '../hooks/useExplainabilityQueries'
import { API_ORIGIN } from '../api/client'
import { formatCurrency, formatDate, formatNumber } from '../utils/format'
import type { ComponentScoreOut, CustomerOrderItem, FeatureContribution, ModelExplanation } from '../api/types'

const FACTOR_LABELS: Record<string, string> = {
  days_since_last_purchase: 'Days Since Last Purchase',
  purchase_frequency: 'Purchase Frequency',
  customer_lifetime_value: 'Customer Lifetime Value',
  average_order_value: 'Average Order Value',
  average_payment_delay: 'Average Payment Delay',
  number_of_orders: 'Number of Orders',
  revenue_generated: 'Revenue Generated (last 90d)',
  order_growth_trend: 'Order Growth Trend',
  seasonal_purchasing_consistency: 'Seasonal Purchasing Consistency',
  months_active: 'Months Active',
  monthly_revenue: 'Monthly Revenue',
  active_months: 'Active Months',
  revenue_growth: 'Revenue Growth',
  order_count_growth: 'Order Count Growth',
  preferred_product_category: 'Preferred Product Category',
  seasonal_purchase_pattern: 'Seasonal Purchase Pattern',
  institution_type: 'Institution Type',
  state: 'State',
}

interface BreakdownRow {
  factor: string
  raw_value: number
  normalized_score: number
  weight: number
  contribution: number
}

function ReasonList({ reasons }: { reasons: string[] }) {
  if (reasons.length === 0) return null
  return (
    <Stack spacing={0.5} sx={{ mt: 1.5 }}>
      {reasons.map((reason, i) => (
        <Typography
          key={i}
          variant="body2"
          sx={{ color: reason.startsWith('+') ? 'success.main' : 'error.main', fontWeight: 500 }}
        >
          {reason}
        </Typography>
      ))}
    </Stack>
  )
}

function FactorChips({
  contributors,
  color,
}: {
  contributors: FeatureContribution[]
  color: 'success' | 'error'
}) {
  if (contributors.length === 0) {
    return (
      <Typography variant="caption" color="text.secondary" display="block">
        None
      </Typography>
    )
  }
  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
      {contributors.map((c) => (
        <Chip
          key={c.feature}
          size="small"
          color={color}
          variant="outlined"
          label={FACTOR_LABELS[c.feature] ?? c.feature.replace(/_/g, ' ')}
        />
      ))}
    </Stack>
  )
}

function ExplanationSection({
  title,
  valueLabel,
  explanation,
  loading,
}: {
  title: string
  valueLabel: React.ReactNode
  explanation: ModelExplanation | null | undefined
  loading: boolean
}) {
  if (loading) {
    return <Skeleton variant="rectangular" height={140} sx={{ mb: 3, borderRadius: 3 }} />
  }

  if (!explanation) {
    return (
      <SectionCard title={title} sx={{ mb: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Not available yet — retrain / rescore to generate this explanation.
        </Typography>
      </SectionCard>
    )
  }

  const plotEntries = Object.entries(explanation.plot_urls)

  return (
    <SectionCard title={title} action={valueLabel} sx={{ mb: 3 }}>
      {explanation.confidence !== null && explanation.confidence !== undefined && (
        <Typography variant="caption" color="text.secondary">
          Confidence: {explanation.confidence.toFixed(0)}%
        </Typography>
      )}

      <ReasonList reasons={explanation.reasons} />

      <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} sx={{ mt: 2 }}>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" fontWeight={600} color="success.main">
            Top Positive Factors
          </Typography>
          <FactorChips contributors={explanation.positive_contributors} color="success" />
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="caption" fontWeight={600} color="error.main">
            Top Negative Factors
          </Typography>
          <FactorChips contributors={explanation.negative_contributors} color="error" />
        </Box>
      </Stack>

      {plotEntries.length > 0 && (
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mt: 2.5 }}>
          {plotEntries.map(([name, url]) => (
            <Box key={name} sx={{ flex: 1 }}>
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                sx={{ mb: 0.5, textTransform: 'capitalize' }}
              >
                {name} plot
              </Typography>
              <Box
                component="img"
                src={`${API_ORIGIN}${url}`}
                alt={`${title} ${name} plot`}
                sx={{ width: '100%', borderRadius: 1, border: '1px solid', borderColor: 'divider' }}
              />
            </Box>
          ))}
        </Stack>
      )}
    </SectionCard>
  )
}

export default function CustomerDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [tab, setTab] = useState(0)
  const customer = useCustomer(id)
  const orders = useCustomerOrders(id)
  const health = useCustomerHealth(id)
  const prediction = useCustomerPrediction(id)
  const explanation = useCustomerExplanation(id)

  if (customer.isError) {
    return <ErrorState message="Customer not found or unreachable." onRetry={() => customer.refetch()} />
  }

  const c = customer.data
  const h = health.data
  const p = prediction.data
  const ex = explanation.data

  const breakdownRows: BreakdownRow[] = h
    ? Object.entries(h.component_breakdown)
        .map(([factor, comp]: [string, ComponentScoreOut]) => ({ factor, ...comp }))
        .sort((a, b) => b.contribution - a.contribution)
    : []

  return (
    <>
      <DetailHeader backLabel="Customers" onBack={() => navigate('/customers')} loading={customer.isLoading || !c}>
        {c && (
          <Box
            sx={{
              display: 'flex',
              flexDirection: { xs: 'column', md: 'row' },
              justifyContent: 'space-between',
              gap: 2,
            }}
          >
            <Box>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }} flexWrap="wrap">
                <Typography variant="h5" fontWeight={700}>
                  {c.name}
                </Typography>
                <StatusChip value={c.institution_type} />
                <StatusChip value={c.status} />
                {h && <StatusChip value={h.health_status} />}
              </Stack>
              <Stack direction="row" spacing={0.5} alignItems="center" sx={{ color: 'text.secondary' }}>
                <PlaceOutlinedIcon fontSize="small" />
                <Typography variant="body2">
                  {c.city}, {c.state} · {c.region} region · onboarded {formatDate(c.onboarded_date)}
                </Typography>
              </Stack>
            </Box>
            <Stack spacing={0.5} sx={{ minWidth: 220 }}>
              <Typography variant="subtitle2" fontWeight={600}>
                {c.contact_name}
              </Typography>
              <Stack direction="row" spacing={0.5} alignItems="center" sx={{ color: 'text.secondary' }}>
                <EmailOutlinedIcon fontSize="small" />
                <Typography variant="body2">{c.contact_email}</Typography>
              </Stack>
              <Stack direction="row" spacing={0.5} alignItems="center" sx={{ color: 'text.secondary' }}>
                <PhoneOutlinedIcon fontSize="small" />
                <Typography variant="body2">{c.contact_phone}</Typography>
              </Stack>
            </Stack>
          </Box>
        )}
      </DetailHeader>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="Overview" />
        <Tab label="Explainability" />
      </Tabs>

      {tab === 0 && (
        <>
          <SectionCard title="Customer Health" sx={{ mb: 3 }}>
            {health.isLoading ? (
              <Skeleton variant="text" width="50%" height={32} />
            ) : health.isError ? (
              <Typography variant="body2" color="text.secondary">
                No health score computed yet for this customer.
              </Typography>
            ) : h ? (
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} alignItems={{ sm: 'center' }}>
                <HealthScoreBar score={h.health_score} status={h.health_status} width={140} />
                <HealthTrendIndicator
                  trend={h.health_trend}
                  currentScore={h.health_score}
                  previousScore={h.previous_health_score}
                />
                <Typography variant="caption" color="text.secondary">
                  Last updated {formatDate(h.last_updated)} · model {h.model_version}
                </Typography>
              </Stack>
            ) : null}
          </SectionCard>

          <SectionCard title="Purchase Prediction" sx={{ mb: 3 }}>
            {prediction.isLoading ? (
              <Skeleton variant="text" width="50%" height={32} />
            ) : prediction.isError ? (
              <Typography variant="body2" color="text.secondary">
                No prediction computed yet for this customer.
              </Typography>
            ) : p ? (
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={4}
                alignItems={{ sm: 'center' }}
              >
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Purchase Probability (next 30 days)
                  </Typography>
                  <ProbabilityBar value={p.purchase_probability} width={140} />
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Expected Order Value
                  </Typography>
                  <Typography variant="h6" fontWeight={700}>
                    {formatCurrency(p.expected_order_value)}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" color="text.secondary" display="block">
                    Confidence
                  </Typography>
                  <Typography variant="h6" fontWeight={700}>
                    {p.confidence_score.toFixed(0)}%
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  Predicted {formatDate(p.prediction_date)} · model {p.model_version}
                </Typography>
              </Stack>
            ) : null}
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1.5 }}>
              See the Explainability tab for why these values were predicted.
            </Typography>
          </SectionCard>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(4, 1fr)' },
              gap: 2,
              mb: 3,
            }}
          >
            <KpiCard
              label="Total Revenue"
              value={c ? formatCurrency(c.total_revenue) : undefined}
              loading={customer.isLoading}
            />
            <KpiCard
              label="Total Orders"
              value={c ? formatNumber(c.total_orders) : undefined}
              loading={customer.isLoading}
            />
            <KpiCard
              label="Average Order Value"
              value={c ? formatCurrency(c.average_order_value) : undefined}
              loading={customer.isLoading}
            />
            <KpiCard
              label="Last Order"
              value={c ? formatDate(c.last_order_date) : undefined}
              loading={customer.isLoading}
            />
          </Box>

          {h && (
            <>
              <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
                Health Score Breakdown
              </Typography>
              <Box sx={{ mb: 3 }}>
                <DataTable<BreakdownRow>
                  columns={[
                    { key: 'factor', label: 'Factor', render: (r) => FACTOR_LABELS[r.factor] ?? r.factor },
                    { key: 'raw_value', label: 'Raw Value', align: 'right', render: (r) => r.raw_value.toLocaleString() },
                    {
                      key: 'normalized_score',
                      label: 'Normalized (0-100)',
                      align: 'right',
                      render: (r) => r.normalized_score.toFixed(1),
                    },
                    { key: 'weight', label: 'Weight', align: 'right', render: (r) => `${(r.weight * 100).toFixed(0)}%` },
                    {
                      key: 'contribution',
                      label: 'Points Contributed',
                      align: 'right',
                      render: (r) => r.contribution.toFixed(2),
                    },
                  ]}
                  rows={breakdownRows}
                  getRowKey={(r) => r.factor}
                  dense
                />
              </Box>
            </>
          )}

          <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
            Order History
          </Typography>
          <DataTable<CustomerOrderItem>
            columns={[
              { key: 'order_number', label: 'Order #', render: (r) => r.order_number },
              { key: 'order_date', label: 'Date', render: (r) => formatDate(r.order_date) },
              { key: 'item_count', label: 'Items', align: 'right', render: (r) => r.item_count },
              { key: 'status', label: 'Status', render: (r) => <StatusChip value={r.status} /> },
              {
                key: 'payment_status',
                label: 'Payment',
                render: (r) => <StatusChip value={r.payment_status} />,
              },
              {
                key: 'total_amount',
                label: 'Amount',
                align: 'right',
                render: (r) => formatCurrency(r.total_amount),
              },
            ]}
            rows={orders.data ?? []}
            getRowKey={(r) => r.id}
            loading={orders.isLoading}
            error={orders.isError}
            onRetry={() => orders.refetch()}
            emptyDescription="This customer has not placed any orders yet."
          />
        </>
      )}

      {tab === 1 && (
        <>
          {explanation.isError && (
            <ErrorState message="Explanations not available for this customer." onRetry={() => explanation.refetch()} />
          )}
          {!explanation.isError && (
            <>
              <ExplanationSection
                title="Customer Health Score"
                valueLabel={
                  ex?.health_score ? (
                    <Typography variant="h6" fontWeight={700}>
                      {ex.health_score.value.toFixed(0)} / 100
                    </Typography>
                  ) : null
                }
                explanation={ex?.health_score}
                loading={explanation.isLoading}
              />
              <ExplanationSection
                title="Purchase Probability"
                valueLabel={
                  ex?.purchase_probability ? (
                    <Typography variant="h6" fontWeight={700}>
                      {ex.purchase_probability.value.toFixed(0)}%
                    </Typography>
                  ) : null
                }
                explanation={ex?.purchase_probability}
                loading={explanation.isLoading}
              />
              <ExplanationSection
                title="Expected Order Value"
                valueLabel={
                  ex?.expected_order_value ? (
                    <Typography variant="h6" fontWeight={700}>
                      {formatCurrency(ex.expected_order_value.value)}
                    </Typography>
                  ) : null
                }
                explanation={ex?.expected_order_value}
                loading={explanation.isLoading}
              />
              {ex?.generated_at && (
                <Typography variant="caption" color="text.secondary">
                  Explanations generated {formatDate(ex.generated_at)}
                </Typography>
              )}
            </>
          )}
        </>
      )}
    </>
  )
}

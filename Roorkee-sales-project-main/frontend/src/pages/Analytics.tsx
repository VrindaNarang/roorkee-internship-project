import { useState } from 'react'
import { Box, Stack, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material'
import { ChartCard } from '../components/charts/ChartCard'
import { CopilotPanel } from '../components/copilot/CopilotPanel'
import { SalesTrendChart } from '../components/charts/SalesTrendChart'
import { OrdersTrendChart } from '../components/charts/OrdersTrendChart'
import { RegionPerformanceChart } from '../components/charts/RegionPerformanceChart'
import { KpiCard } from '../components/dashboard/KpiCard'
import { StatusChip } from '../components/common/StatusChip'
import { PageIntro } from '../components/common/PageIntro'
import { SectionCard } from '../components/common/SectionCard'
import {
  useAnalyticsSalesTrend,
  useCustomerInsights,
  useRegionPerformance,
} from '../hooks/useAnalyticsQueries'
import { formatCurrency, formatNumber } from '../utils/format'

const RANGE_OPTIONS = [
  { value: 6, label: '6M' },
  { value: 12, label: '12M' },
  { value: 24, label: '24M' },
]

export default function Analytics() {
  const [months, setMonths] = useState(12)
  const salesTrend = useAnalyticsSalesTrend(months)
  const regionPerformance = useRegionPerformance()
  const customerInsights = useCustomerInsights()

  return (
    <>
      <PageIntro description="Deeper analysis of revenue trends, regional performance, and customer composition." />

      <Typography variant="h6" fontWeight={600} sx={{ mb: 1.5 }}>
        Revenue Analytics
      </Typography>
      <Box sx={{ mb: 4 }}>
        <ChartCard
          title="Revenue Trend"
          subtitle="Monthly revenue over the selected period"
          loading={salesTrend.isLoading}
          error={salesTrend.isError}
          onRetry={() => salesTrend.refetch()}
          isEmpty={(salesTrend.data ?? []).length === 0}
          action={
            <ToggleButtonGroup
              size="small"
              exclusive
              value={months}
              onChange={(_, value) => value && setMonths(value)}
            >
              {RANGE_OPTIONS.map((opt) => (
                <ToggleButton key={opt.value} value={opt.value} sx={{ px: 1.5 }}>
                  {opt.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          }
        >
          <SalesTrendChart data={salesTrend.data ?? []} />
        </ChartCard>
      </Box>

      <Typography variant="h6" fontWeight={600} sx={{ mb: 1.5 }}>
        Sales Trends
      </Typography>
      <Box sx={{ mb: 4 }}>
        <ChartCard
          title="Order Volume"
          subtitle="Number of orders placed per month"
          loading={salesTrend.isLoading}
          error={salesTrend.isError}
          onRetry={() => salesTrend.refetch()}
          isEmpty={(salesTrend.data ?? []).length === 0}
          height={280}
        >
          <OrdersTrendChart data={salesTrend.data ?? []} />
        </ChartCard>
      </Box>

      <Typography variant="h6" fontWeight={600} sx={{ mb: 1.5 }}>
        Regional Performance
      </Typography>
      <Box sx={{ mb: 4 }}>
        <ChartCard
          title="Revenue by Region"
          subtitle="All regions ranked by total revenue"
          loading={regionPerformance.isLoading}
          error={regionPerformance.isError}
          onRetry={() => regionPerformance.refetch()}
          isEmpty={(regionPerformance.data ?? []).length === 0}
        >
          <RegionPerformanceChart data={regionPerformance.data ?? []} />
        </ChartCard>
      </Box>

      <Typography variant="h6" fontWeight={600} sx={{ mb: 1.5 }}>
        Customer Insights
      </Typography>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)' },
          gap: 2,
          mb: 3,
        }}
      >
        <KpiCard
          label="New Customers (90d)"
          value={customerInsights.data ? formatNumber(customerInsights.data.new_customers_last_90_days) : undefined}
          loading={customerInsights.isLoading}
        />
        <KpiCard
          label="At-Risk Customers"
          value={customerInsights.data ? formatNumber(customerInsights.data.at_risk_customers) : undefined}
          loading={customerInsights.isLoading}
        />
        <KpiCard
          label="Repeat Customer Rate"
          value={customerInsights.data ? `${customerInsights.data.repeat_customer_pct.toFixed(1)}%` : undefined}
          loading={customerInsights.isLoading}
        />
      </Box>

      <SectionCard title="Revenue by Institution Type">
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3}>
          {(customerInsights.data?.institution_type_breakdown ?? []).map((entry) => (
            <Box key={entry.institution_type} sx={{ flex: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <StatusChip value={entry.institution_type} />
                <Typography variant="body2" color="text.secondary">
                  {formatNumber(entry.customer_count)} customers
                </Typography>
              </Stack>
              <Typography variant="h5" fontWeight={700}>
                {formatCurrency(entry.revenue)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Avg order value {formatCurrency(entry.avg_order_value)}
              </Typography>
            </Box>
          ))}
        </Stack>
      </SectionCard>

      <CopilotPanel />
    </>
  )
}

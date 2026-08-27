import { useTheme } from '@mui/material/styles'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { FeatureContribution } from '../../api/types'
import { getGridColor } from '../../theme/chartPalette'
import { ChartTooltip } from './ChartTooltip'

export const FEATURE_LABELS: Record<string, string> = {
  days_since_last_purchase: 'Days Since Last Purchase',
  purchase_frequency: 'Purchase Frequency',
  customer_lifetime_value: 'Customer Lifetime Value',
  average_order_value: 'Average Order Value',
  monthly_revenue: 'Revenue Generated',
  active_months: 'Months Active',
  average_payment_delay: 'Average Payment Delay',
  health_score: 'Health Score',
  revenue_growth: 'Revenue Trend',
  order_count_growth: 'Order Growth',
  preferred_product_category: 'Preferred Category',
  seasonal_purchase_pattern: 'Seasonality',
  institution_type: 'Customer Type',
  state: 'State',
}

interface ContributionChartProps {
  data: FeatureContribution[]
  height?: number
}

export function ContributionChart({ data, height = 220 }: ContributionChartProps) {
  const theme = useTheme()
  const grid = getGridColor(theme.palette.mode)

  const chartData = [...data]
    .sort((a, b) => Math.abs(a.value) - Math.abs(b.value))
    .map((d) => ({ ...d, label: FEATURE_LABELS[d.feature] ?? d.feature }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={grid} strokeDasharray="3 3" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          axisLine={{ stroke: theme.palette.divider }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          axisLine={false}
          tickLine={false}
          width={140}
        />
        <Tooltip
          cursor={{ fill: theme.palette.action.hover }}
          content={
            <ChartTooltip
              formatter={(point: FeatureContribution & { label: string }) => [
                {
                  label: point.direction === 'increases' ? 'Increases likelihood' : 'Decreases likelihood',
                  value: point.value.toFixed(2),
                  color: point.direction === 'increases' ? theme.palette.success.main : theme.palette.error.main,
                },
              ]}
              labelFormatter={(point: FeatureContribution & { label: string }) => point.label}
            />
          }
        />
        <Bar dataKey="value" radius={[4, 4, 4, 4]} maxBarSize={18} isAnimationActive={false}>
          {chartData.map((entry) => (
            <Cell
              key={entry.feature}
              fill={entry.direction === 'increases' ? theme.palette.success.main : theme.palette.error.main}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

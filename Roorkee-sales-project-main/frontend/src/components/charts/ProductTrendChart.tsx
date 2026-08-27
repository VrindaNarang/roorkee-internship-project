import { useTheme } from '@mui/material/styles'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ProductSalesTrendPoint } from '../../api/types'
import { getGridColor, getSequentialColor } from '../../theme/chartPalette'
import { formatCompactCurrency, formatMonth, formatNumber } from '../../utils/format'
import { ChartTooltip } from './ChartTooltip'

interface ProductTrendChartProps {
  data: ProductSalesTrendPoint[]
}

export function ProductTrendChart({ data }: ProductTrendChartProps) {
  const theme = useTheme()
  const mode = theme.palette.mode
  const color = getSequentialColor(mode)
  const grid = getGridColor(mode)

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="productRevenueFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.28} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={grid} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="month"
          tickFormatter={formatMonth}
          tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          axisLine={{ stroke: theme.palette.divider }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={formatCompactCurrency}
          tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          axisLine={false}
          tickLine={false}
          width={64}
        />
        <Tooltip
          content={
            <ChartTooltip
              formatter={(point: ProductSalesTrendPoint) => [
                { label: 'Revenue', value: formatCompactCurrency(point.revenue) },
                { label: 'Units sold', value: formatNumber(point.quantity) },
              ]}
              labelFormatter={(point: ProductSalesTrendPoint) => formatMonth(point.month)}
            />
          }
        />
        <Area
          type="monotone"
          dataKey="revenue"
          stroke={color}
          strokeWidth={2}
          fill="url(#productRevenueFill)"
          dot={false}
          activeDot={{ r: 5 }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

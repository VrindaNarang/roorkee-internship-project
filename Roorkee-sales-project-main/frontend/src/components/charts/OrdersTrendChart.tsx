import { useTheme } from '@mui/material/styles'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SalesTrendPoint } from '../../api/types'
import { getGridColor, getSequentialColor } from '../../theme/chartPalette'
import { formatMonth, formatNumber } from '../../utils/format'
import { ChartTooltip } from './ChartTooltip'

interface OrdersTrendChartProps {
  data: SalesTrendPoint[]
}

export function OrdersTrendChart({ data }: OrdersTrendChartProps) {
  const theme = useTheme()
  const mode = theme.palette.mode
  const color = getSequentialColor(mode)
  const grid = getGridColor(mode)

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={grid} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="month"
          tickFormatter={formatMonth}
          tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          axisLine={{ stroke: theme.palette.divider }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={formatNumber}
          tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        <Tooltip
          cursor={{ fill: theme.palette.action.hover }}
          content={
            <ChartTooltip
              formatter={(point: SalesTrendPoint) => [
                { label: 'Orders', value: formatNumber(point.orders), color },
              ]}
              labelFormatter={(point: SalesTrendPoint) => formatMonth(point.month)}
            />
          }
        />
        <Bar
          dataKey="orders"
          fill={color}
          radius={[4, 4, 0, 0]}
          maxBarSize={28}
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}

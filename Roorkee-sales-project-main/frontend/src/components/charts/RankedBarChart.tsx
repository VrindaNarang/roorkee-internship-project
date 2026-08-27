import { useTheme } from '@mui/material/styles'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getGridColor, getSequentialColor } from '../../theme/chartPalette'
import { formatCompactCurrency } from '../../utils/format'
import { ChartTooltip } from './ChartTooltip'

interface RankedBarChartProps<T> {
  data: T[]
  categoryKey: keyof T
  valueKey: keyof T
  limit?: number
  tooltipRows: (point: T) => { label: string; value: string; color?: string }[]
  tooltipLabel: (point: T) => string
  valueFormatter?: (value: number) => string
}

export function RankedBarChart<T>({
  data,
  categoryKey,
  valueKey,
  limit = 8,
  tooltipRows,
  tooltipLabel,
  valueFormatter = formatCompactCurrency,
}: RankedBarChartProps<T>) {
  const theme = useTheme()
  const mode = theme.palette.mode
  const color = getSequentialColor(mode)
  const grid = getGridColor(mode)
  const chartData = data.slice(0, limit)

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid stroke={grid} strokeDasharray="3 3" horizontal={false} />
        <XAxis
          type="number"
          tickFormatter={valueFormatter}
          tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey={categoryKey as string}
          tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          axisLine={false}
          tickLine={false}
          width={110}
        />
        <Tooltip
          cursor={{ fill: theme.palette.action.hover }}
          content={<ChartTooltip formatter={tooltipRows} labelFormatter={tooltipLabel} />}
        />
        <Bar
          dataKey={valueKey as string}
          fill={color}
          radius={[0, 4, 4, 0]}
          maxBarSize={18}
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}

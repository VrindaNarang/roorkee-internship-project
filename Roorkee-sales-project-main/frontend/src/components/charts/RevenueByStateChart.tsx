import { useTheme } from '@mui/material/styles'
import type { RevenueByState } from '../../api/types'
import { getSequentialColor } from '../../theme/chartPalette'
import { formatCompactCurrency, formatNumber } from '../../utils/format'
import { RankedBarChart } from './RankedBarChart'

interface RevenueByStateChartProps {
  data: RevenueByState[]
  limit?: number
}

export function RevenueByStateChart({ data, limit = 8 }: RevenueByStateChartProps) {
  const theme = useTheme()
  const color = getSequentialColor(theme.palette.mode)

  return (
    <RankedBarChart
      data={data}
      categoryKey="state"
      valueKey="revenue"
      limit={limit}
      tooltipRows={(point) => [
        { label: 'Revenue', value: formatCompactCurrency(point.revenue), color },
        { label: 'Orders', value: formatNumber(point.orders) },
      ]}
      tooltipLabel={(point) => `${point.state} · ${point.region}`}
    />
  )
}

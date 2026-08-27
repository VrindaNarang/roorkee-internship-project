import { useTheme } from '@mui/material/styles'
import type { RegionPerformance } from '../../api/types'
import { getSequentialColor } from '../../theme/chartPalette'
import { formatCompactCurrency, formatNumber } from '../../utils/format'
import { RankedBarChart } from './RankedBarChart'

interface RegionPerformanceChartProps {
  data: RegionPerformance[]
}

export function RegionPerformanceChart({ data }: RegionPerformanceChartProps) {
  const theme = useTheme()
  const color = getSequentialColor(theme.palette.mode)

  return (
    <RankedBarChart
      data={data}
      categoryKey="region"
      valueKey="revenue"
      limit={data.length}
      tooltipRows={(point) => [
        { label: 'Revenue', value: formatCompactCurrency(point.revenue), color },
        { label: 'Orders', value: formatNumber(point.orders) },
        { label: 'Customers', value: formatNumber(point.customer_count) },
        { label: 'Avg order', value: formatCompactCurrency(point.avg_order_value) },
      ]}
      tooltipLabel={(point) => point.region}
    />
  )
}

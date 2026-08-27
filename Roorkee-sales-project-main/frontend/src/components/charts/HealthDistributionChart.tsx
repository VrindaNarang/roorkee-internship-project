import { useMemo } from 'react'
import { useTheme } from '@mui/material/styles'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { CustomerHealthListItem } from '../../api/types'
import { getGridColor } from '../../theme/chartPalette'
import { ChartTooltip } from './ChartTooltip'

interface HealthDistributionChartProps {
  data: CustomerHealthListItem[]
}

interface Bucket {
  range: string
  count: number
  band: 'critical' | 'at_risk' | 'healthy'
}

const BUCKET_SIZE = 10

function buildBuckets(data: CustomerHealthListItem[]): Bucket[] {
  const buckets: Bucket[] = Array.from({ length: 10 }, (_, i) => {
    const lower = i * BUCKET_SIZE
    const band = lower >= 80 ? 'healthy' : lower >= 50 ? 'at_risk' : 'critical'
    return { range: `${lower}-${lower + 9}`, count: 0, band }
  })

  for (const item of data) {
    const idx = Math.min(9, Math.floor(item.health_score / BUCKET_SIZE))
    buckets[idx].count += 1
  }
  return buckets
}

export function HealthDistributionChart({ data }: HealthDistributionChartProps) {
  const theme = useTheme()
  const grid = getGridColor(theme.palette.mode)
  const buckets = useMemo(() => buildBuckets(data), [data])

  const bandColor: Record<Bucket['band'], string> = {
    healthy: theme.palette.success.main,
    at_risk: theme.palette.warning.main,
    critical: theme.palette.error.main,
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={buckets} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={grid} strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="range"
          tick={{ fontSize: 11, fill: theme.palette.text.secondary }}
          axisLine={{ stroke: theme.palette.divider }}
          tickLine={false}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 12, fill: theme.palette.text.secondary }}
          axisLine={false}
          tickLine={false}
          width={32}
        />
        <Tooltip
          cursor={{ fill: theme.palette.action.hover }}
          content={
            <ChartTooltip
              formatter={(point: Bucket) => [{ label: 'Customers', value: String(point.count) }]}
              labelFormatter={(point: Bucket) => `Score ${point.range}`}
            />
          }
        />
        <Bar dataKey="count" radius={[4, 4, 0, 0]} maxBarSize={36} isAnimationActive={false}>
          {buckets.map((bucket) => (
            <Cell key={bucket.range} fill={bandColor[bucket.band]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

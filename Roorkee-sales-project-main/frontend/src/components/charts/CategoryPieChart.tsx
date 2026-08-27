import { Box, Stack, Typography } from '@mui/material'
import { useTheme } from '@mui/material/styles'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import type { CategoryDistribution } from '../../api/types'
import { getCategoricalPalette } from '../../theme/chartPalette'
import { formatCompactCurrency } from '../../utils/format'
import { ChartTooltip } from './ChartTooltip'

interface CategoryPieChartProps {
  data: CategoryDistribution[]
}

export function CategoryPieChart({ data }: CategoryPieChartProps) {
  const theme = useTheme()
  const palette = getCategoricalPalette(theme.palette.mode)

  return (
    <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, height: '100%', gap: 2 }}>
      <Box sx={{ flex: 1, minWidth: 0, height: '100%' }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="revenue"
              nameKey="category"
              innerRadius="55%"
              outerRadius="85%"
              paddingAngle={2}
              stroke={theme.palette.background.paper}
              strokeWidth={2}
              isAnimationActive={false}
            >
              {data.map((entry, index) => (
                <Cell key={entry.category} fill={palette[index % palette.length]} />
              ))}
            </Pie>
            <Tooltip
              content={
                <ChartTooltip
                  formatter={(point: CategoryDistribution) => [
                    { label: 'Revenue', value: formatCompactCurrency(point.revenue) },
                    { label: 'Share', value: `${point.pct_of_revenue.toFixed(1)}%` },
                  ]}
                  labelFormatter={(point: CategoryDistribution) => point.category}
                />
              }
            />
          </PieChart>
        </ResponsiveContainer>
      </Box>
      <Stack
        justifyContent="center"
        spacing={1}
        sx={{ width: { xs: '100%', sm: 170 }, flexShrink: 0, py: { xs: 0, sm: 1 } }}
      >
        {data.map((entry, index) => (
          <Box key={entry.category} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                bgcolor: palette[index % palette.length],
                flexShrink: 0,
              }}
            />
            <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }} noWrap>
              {entry.category}
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {entry.pct_of_revenue.toFixed(0)}%
            </Typography>
          </Box>
        ))}
      </Stack>
    </Box>
  )
}

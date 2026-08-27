import { Box, Paper, Typography } from '@mui/material'

interface TooltipRow {
  label: string
  value: string
  color?: string
}

interface ChartTooltipProps<T> {
  active?: boolean
  payload?: { payload: T }[]
  formatter: (point: T) => TooltipRow[]
  labelFormatter?: (point: T) => string
}

export function ChartTooltip<T>({ active, payload, formatter, labelFormatter }: ChartTooltipProps<T>) {
  if (!active || !payload || payload.length === 0) return null
  const point = payload[0].payload
  const rows = formatter(point)

  return (
    <Paper
      variant="outlined"
      sx={{ px: 1.5, py: 1, minWidth: 140, borderRadius: 2, boxShadow: 4, backgroundColor: 'background.paper' }}
    >
      {labelFormatter && (
        <Typography variant="caption" fontWeight={700} sx={{ display: 'block', mb: 0.5 }}>
          {labelFormatter(point)}
        </Typography>
      )}
      {rows.map((row) => (
        <Box key={row.label} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, py: 0.25 }}>
          {row.color && (
            <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: row.color, flexShrink: 0 }} />
          )}
          <Typography variant="caption" color="text.secondary" sx={{ flexGrow: 1 }}>
            {row.label}
          </Typography>
          <Typography variant="caption" fontWeight={700}>
            {row.value}
          </Typography>
        </Box>
      ))}
    </Paper>
  )
}

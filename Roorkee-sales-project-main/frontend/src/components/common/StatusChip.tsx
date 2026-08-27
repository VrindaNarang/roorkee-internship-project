import { Chip } from '@mui/material'

type ChipColor = 'success' | 'warning' | 'error' | 'default' | 'info'

const COLOR_MAP: Record<string, ChipColor> = {
  active: 'success',
  fulfilled: 'success',
  paid: 'success',
  healthy: 'success',
  dormant: 'default',
  inactive: 'default',
  pending: 'warning',
  at_risk: 'warning',
  overdue: 'error',
  cancelled: 'error',
  critical: 'error',
  government: 'info',
  private: 'default',
  university: 'info',
  research_lab: 'default',
  industry: 'default',
  high: 'error',
  medium: 'warning',
  low: 'success',
}

interface StatusChipProps {
  value: string
}

export function StatusChip({ value }: StatusChipProps) {
  const color = COLOR_MAP[value] ?? 'default'
  return (
    <Chip
      size="small"
      label={value.replace(/_/g, ' ')}
      color={color}
      variant={color === 'default' ? 'outlined' : 'filled'}
      sx={{ textTransform: 'capitalize', fontWeight: 600 }}
    />
  )
}

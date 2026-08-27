import { useTheme } from '@mui/material/styles'
import { ProgressBar } from '../common/ProgressBar'
import type { HealthStatus } from '../../api/types'

interface HealthScoreBarProps {
  score: number
  status: HealthStatus
  width?: number
}

const STATUS_COLOR_KEY: Record<HealthStatus, 'success' | 'warning' | 'error'> = {
  healthy: 'success',
  at_risk: 'warning',
  critical: 'error',
}

export function HealthScoreBar({ score, status, width = 90 }: HealthScoreBarProps) {
  const theme = useTheme()
  const color = theme.palette[STATUS_COLOR_KEY[status]].main

  return <ProgressBar value={score} color={color} width={width} label={score.toFixed(0)} />
}

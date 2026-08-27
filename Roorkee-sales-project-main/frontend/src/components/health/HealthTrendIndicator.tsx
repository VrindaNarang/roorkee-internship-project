import { Stack, Tooltip, Typography } from '@mui/material'
import TrendingUpRoundedIcon from '@mui/icons-material/TrendingUpRounded'
import TrendingDownRoundedIcon from '@mui/icons-material/TrendingDownRounded'
import TrendingFlatRoundedIcon from '@mui/icons-material/TrendingFlatRounded'
import FiberNewRoundedIcon from '@mui/icons-material/FiberNewRounded'
import type { HealthTrend } from '../../api/types'

interface HealthTrendIndicatorProps {
  trend: HealthTrend
  currentScore: number
  previousScore: number | null
}

export function HealthTrendIndicator({ trend, currentScore, previousScore }: HealthTrendIndicatorProps) {
  if (trend === 'new' || previousScore === null) {
    return (
      <Tooltip title="First score computed for this customer — no prior run to compare">
        <Stack direction="row" spacing={0.5} alignItems="center" sx={{ color: 'text.secondary' }}>
          <FiberNewRoundedIcon fontSize="small" />
          <Typography variant="caption">New</Typography>
        </Stack>
      </Tooltip>
    )
  }

  const delta = currentScore - previousScore
  const config = {
    improving: { icon: <TrendingUpRoundedIcon fontSize="small" />, color: 'success.main' as const },
    declining: { icon: <TrendingDownRoundedIcon fontSize="small" />, color: 'error.main' as const },
    stable: { icon: <TrendingFlatRoundedIcon fontSize="small" />, color: 'text.secondary' as const },
  }[trend]

  return (
    <Tooltip title={`Previous score: ${previousScore.toFixed(0)}`}>
      <Stack direction="row" spacing={0.5} alignItems="center" sx={{ color: config.color }}>
        {config.icon}
        <Typography variant="caption" fontWeight={600}>
          {delta > 0 ? '+' : ''}
          {delta.toFixed(1)}
        </Typography>
      </Stack>
    </Tooltip>
  )
}

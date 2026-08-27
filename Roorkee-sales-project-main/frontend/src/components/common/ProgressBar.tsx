import { Box, Typography } from '@mui/material'
import { useTheme } from '@mui/material/styles'

interface ProgressBarProps {
  value: number // 0-100
  color: string
  width?: number
  label: string
}

// Shared mini progress-bar rendering used by HealthScoreBar and
// ProbabilityBar — same track/fill, only the color + label differ per caller.
export function ProgressBar({ value, color, width = 90, label }: ProgressBarProps) {
  const theme = useTheme()
  const clamped = Math.max(0, Math.min(100, value))

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Box
        sx={{
          width,
          height: 6,
          borderRadius: 3,
          bgcolor: theme.palette.action.hover,
          overflow: 'hidden',
          flexShrink: 0,
        }}
      >
        <Box
          sx={{
            width: `${clamped}%`,
            height: '100%',
            bgcolor: color,
            borderRadius: 3,
            transition: 'width 300ms cubic-bezier(0.4, 0, 0.2, 1)',
          }}
        />
      </Box>
      <Typography variant="body2" fontWeight={700} sx={{ minWidth: 40, color }}>
        {label}
      </Typography>
    </Box>
  )
}

import { useTheme } from '@mui/material/styles'
import { ProgressBar } from '../common/ProgressBar'

interface ProbabilityBarProps {
  value: number // 0-100
  width?: number
}

export function ProbabilityBar({ value, width = 90 }: ProbabilityBarProps) {
  const theme = useTheme()
  const color =
    value >= 70 ? theme.palette.success.main : value >= 40 ? theme.palette.warning.main : theme.palette.error.main

  return <ProgressBar value={value} color={color} width={width} label={`${value.toFixed(0)}%`} />
}

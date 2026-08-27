import { Box, Paper, Skeleton, Typography } from '@mui/material'
import type { ReactNode } from 'react'
import { EmptyState } from '../common/EmptyState'
import { ErrorState } from '../common/ErrorState'

interface ChartCardProps {
  title: string
  subtitle?: string
  height?: number
  loading?: boolean
  error?: boolean
  errorMessage?: string
  onRetry?: () => void
  isEmpty?: boolean
  children: ReactNode
  action?: ReactNode
}

export function ChartCard({
  title,
  subtitle,
  height = 340,
  loading,
  error,
  errorMessage,
  onRetry,
  isEmpty,
  children,
  action,
}: ChartCardProps) {
  return (
    <Paper variant="outlined" sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
        <Box>
          <Typography variant="subtitle1" fontWeight={600}>
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        {action}
      </Box>

      <Box sx={{ height, flexShrink: 0, display: 'flex', flexDirection: 'column' }}>
        {loading ? (
          <Skeleton variant="rounded" width="100%" height={height} />
        ) : error ? (
          <ErrorState message={errorMessage} onRetry={onRetry} />
        ) : isEmpty ? (
          <EmptyState description="No data available for this period yet." />
        ) : (
          children
        )}
      </Box>
    </Paper>
  )
}

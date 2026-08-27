import { Box, IconButton, Paper, Skeleton, Stack, Typography } from '@mui/material'
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded'
import type { ReactNode } from 'react'

interface DetailHeaderProps {
  backLabel: string
  onBack: () => void
  loading?: boolean
  children: ReactNode
}

// Shared back-button row + header card used by detail pages (customer,
// product): standardizes the back link and the loading-skeleton header.
export function DetailHeader({ backLabel, onBack, loading, children }: DetailHeaderProps) {
  return (
    <>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <IconButton onClick={onBack} size="small" aria-label={`Back to ${backLabel}`}>
          <ArrowBackRoundedIcon fontSize="small" />
        </IconButton>
        <Typography variant="body2" color="text.secondary">
          Back to {backLabel}
        </Typography>
      </Box>

      <Paper variant="outlined" sx={{ p: 3, mb: 3 }}>
        {loading ? (
          <Stack spacing={1}>
            <Skeleton variant="text" width="40%" height={36} />
            <Skeleton variant="text" width="50%" />
          </Stack>
        ) : (
          children
        )}
      </Paper>
    </>
  )
}

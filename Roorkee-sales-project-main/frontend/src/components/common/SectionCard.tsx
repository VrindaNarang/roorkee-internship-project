import { Box, Paper, Typography, type SxProps, type Theme } from '@mui/material'
import type { ReactNode } from 'react'

interface SectionCardProps {
  title?: string
  subtitle?: string
  action?: ReactNode
  children: ReactNode
  sx?: SxProps<Theme>
  dense?: boolean
}

// Standardized "Paper with a header" wrapper used across detail/analytics/
// recommendations/settings pages, so title/subtitle spacing never drifts.
export function SectionCard({ title, subtitle, action, children, sx, dense }: SectionCardProps) {
  return (
    <Paper variant="outlined" sx={{ p: dense ? 2.5 : 3, height: '100%', ...sx }}>
      {(title || action) && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 2,
            mb: subtitle ? 0.5 : 2,
          }}
        >
          <Box>
            {title && (
              <Typography variant="subtitle1" fontWeight={600}>
                {title}
              </Typography>
            )}
            {subtitle && (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25, mb: 1.5 }}>
                {subtitle}
              </Typography>
            )}
          </Box>
          {action}
        </Box>
      )}
      {children}
    </Paper>
  )
}

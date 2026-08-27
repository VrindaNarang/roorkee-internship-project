import { Box, Typography } from '@mui/material'
import type { ReactNode } from 'react'

interface PageIntroProps {
  description?: string
  action?: ReactNode
}

// Consistent "description line + optional trailing action" row used at the
// top of pages and above sub-sections, in place of ad hoc Typography.
export function PageIntro({ description, action }: PageIntroProps) {
  if (!description && !action) return null
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 2,
        mb: 3,
      }}
    >
      {description && (
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      )}
      {action}
    </Box>
  )
}

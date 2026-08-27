import { Box, Typography } from '@mui/material'
import InboxOutlinedIcon from '@mui/icons-material/InboxOutlined'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  title?: string
  description?: string
  icon?: ReactNode
}

export function EmptyState({
  title = 'Nothing to show yet',
  description = 'Data will appear here once it becomes available.',
  icon,
}: EmptyStateProps) {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 1,
        py: 6,
        px: 2,
        color: 'text.secondary',
        textAlign: 'center',
      }}
    >
      {icon ?? <InboxOutlinedIcon sx={{ fontSize: 36, opacity: 0.5 }} />}
      <Typography variant="subtitle2" fontWeight={600} color="text.primary">
        {title}
      </Typography>
      <Typography variant="body2" sx={{ maxWidth: 320 }}>
        {description}
      </Typography>
    </Box>
  )
}

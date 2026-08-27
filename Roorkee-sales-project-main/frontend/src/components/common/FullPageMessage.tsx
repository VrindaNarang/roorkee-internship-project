import { Box, Button, Typography } from '@mui/material'
import ArrowBackRoundedIcon from '@mui/icons-material/ArrowBackRounded'
import type { ReactNode } from 'react'

interface FullPageMessageProps {
  visual: ReactNode
  title: string
  description: string
  actionLabel?: string
  onAction?: () => void
}

// Full-viewport centered message used for pages rendered outside the app
// shell (404, forbidden) — standardizes the layout, icon/hero spacing, and CTA.
export function FullPageMessage({ visual, title, description, actionLabel, onAction }: FullPageMessageProps) {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        p: 3,
        bgcolor: 'background.default',
      }}
    >
      {visual}
      <Typography variant="h6" fontWeight={600} sx={{ mt: 1.5 }}>
        {title}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 3, maxWidth: 380 }}>
        {description}
      </Typography>
      {actionLabel && onAction && (
        <Button variant="contained" startIcon={<ArrowBackRoundedIcon />} onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </Box>
  )
}

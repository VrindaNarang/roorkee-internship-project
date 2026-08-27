import { Paper, Stack } from '@mui/material'
import type { ReactNode } from 'react'

interface FilterBarProps {
  children: ReactNode
  action?: ReactNode
}

// Layout-only wrapper for filter rows (search + selects/sliders/etc.) so
// every list page shares the same spacing, wrapping, and surface treatment.
export function FilterBar({ children, action }: FilterBarProps) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1.5,
        mb: 2.5,
        display: 'flex',
        flexDirection: { xs: 'column', md: 'row' },
        alignItems: { xs: 'stretch', md: 'center' },
        justifyContent: 'space-between',
        gap: 1.5,
      }}
    >
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1.5}
        alignItems={{ xs: 'stretch', sm: 'center' }}
        flexWrap="wrap"
        useFlexGap
        sx={{ flex: 1 }}
      >
        {children}
      </Stack>
      {action}
    </Paper>
  )
}

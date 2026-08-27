import { Box, Card, CardContent, Skeleton, Typography } from '@mui/material'
import { alpha } from '@mui/material/styles'
import ArrowUpwardRoundedIcon from '@mui/icons-material/ArrowUpwardRounded'
import ArrowDownwardRoundedIcon from '@mui/icons-material/ArrowDownwardRounded'
import type { ReactNode } from 'react'

interface KpiCardProps {
  label: string
  value?: string
  icon?: ReactNode
  trendPct?: number
  loading?: boolean
}

export function KpiCard({ label, value, icon, trendPct, loading }: KpiCardProps) {
  const trendUp = trendPct !== undefined && trendPct >= 0

  return (
    <Card
      sx={{
        transition: 'box-shadow 150ms cubic-bezier(0.4, 0, 0.2, 1), transform 150ms cubic-bezier(0.4, 0, 0.2, 1)',
        '&:hover': { boxShadow: 3, transform: 'translateY(-1px)' },
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
          <Typography variant="body2" color="text.secondary" fontWeight={500}>
            {label}
          </Typography>
          {icon && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 34,
                height: 34,
                borderRadius: 2.5,
                bgcolor: (t) => alpha(t.palette.primary.main, t.palette.mode === 'light' ? 0.1 : 0.18),
                color: 'primary.main',
              }}
            >
              {icon}
            </Box>
          )}
        </Box>

        {loading ? (
          <Skeleton variant="text" width="70%" height={36} sx={{ mt: 0.5 }} />
        ) : (
          <Typography variant="h5" fontWeight={700} sx={{ mt: 0.5, letterSpacing: '-0.01em' }}>
            {value}
          </Typography>
        )}

        {trendPct !== undefined && !loading && (
          <Box
            sx={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 0.25,
              mt: 1,
              px: 0.75,
              py: 0.25,
              borderRadius: 999,
              bgcolor: (t) => alpha(t.palette[trendUp ? 'success' : 'error'].main, t.palette.mode === 'light' ? 0.1 : 0.18),
              color: trendUp ? 'success.main' : 'error.main',
            }}
          >
            {trendUp ? (
              <ArrowUpwardRoundedIcon sx={{ fontSize: 13 }} />
            ) : (
              <ArrowDownwardRoundedIcon sx={{ fontSize: 13 }} />
            )}
            <Typography variant="caption" sx={{ fontWeight: 700 }}>
              {Math.abs(trendPct).toFixed(1)}%
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  )
}

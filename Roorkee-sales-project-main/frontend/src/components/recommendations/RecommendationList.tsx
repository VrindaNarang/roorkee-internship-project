import { Box, Paper, Skeleton, Stack, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { StatusChip } from '../common/StatusChip'
import { EmptyState } from '../common/EmptyState'
import { ErrorState } from '../common/ErrorState'
import type { Recommendation } from '../../api/types'

interface RecommendationListProps {
  items: Recommendation[]
  loading?: boolean
  error?: boolean
  onRetry?: () => void
  emptyDescription?: string
  skeletonRows?: number
}

// Shared feed renderer for every Recommendations page section — each
// Recommendation is a full sentence (title + reason), not tabular data, so
// a card list reads better here than DataTable's dense rows.
export function RecommendationList({
  items,
  loading,
  error,
  onRetry,
  emptyDescription,
  skeletonRows = 3,
}: RecommendationListProps) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <Stack spacing={1.5}>
        {Array.from({ length: skeletonRows }).map((_, i) => (
          <Skeleton key={i} variant="rectangular" height={68} sx={{ borderRadius: 1 }} />
        ))}
      </Stack>
    )
  }

  if (error) {
    return <ErrorState message="Could not load recommendations." onRetry={onRetry} />
  }

  if (items.length === 0) {
    return <EmptyState title="Nothing here right now" description={emptyDescription} />
  }

  return (
    <Stack spacing={1.5}>
      {items.map((item, i) => (
        <Paper
          key={`${item.rule_id}-${item.college_id ?? item.region ?? i}`}
          variant="outlined"
          sx={{
            p: 2,
            cursor: item.college_id ? 'pointer' : 'default',
            transition: 'border-color 150ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 150ms cubic-bezier(0.4, 0, 0.2, 1), transform 150ms cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': item.college_id
              ? { borderColor: 'primary.main', boxShadow: 3, transform: 'translateY(-1px)' }
              : undefined,
          }}
          onClick={item.college_id ? () => navigate(`/customers/${item.college_id}`) : undefined}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1.5}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="body2" fontWeight={600}>
                {item.title}
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                {item.reason}
              </Typography>
            </Box>
            <StatusChip value={item.priority} />
          </Stack>
        </Paper>
      ))}
    </Stack>
  )
}

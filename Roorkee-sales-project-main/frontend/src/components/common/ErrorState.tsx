import { Alert, AlertTitle, Button } from '@mui/material'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'

interface ErrorStateProps {
  message?: string
  onRetry?: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <Alert
      severity="error"
      sx={{ my: 2 }}
      action={
        onRetry ? (
          <Button color="inherit" size="small" startIcon={<RefreshRoundedIcon />} onClick={onRetry}>
            Retry
          </Button>
        ) : undefined
      }
    >
      <AlertTitle>Failed to load data</AlertTitle>
      {message ?? 'Something went wrong while talking to the backend. Please try again.'}
    </Alert>
  )
}

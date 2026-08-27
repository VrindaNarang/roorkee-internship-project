import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Box, Button, Typography } from '@mui/material'
import ReportProblemOutlinedIcon from '@mui/icons-material/ReportProblemOutlined'
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  error: Error | null
}

// A React Query fetch failure never lands here (those render their own
// ErrorState inline) — this only catches genuine render-time crashes (a
// null-reference bug, a malformed prop) so one broken component can't take
// down the entire app with a blank white screen.
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
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
          }}
        >
          <ReportProblemOutlinedIcon color="error" sx={{ fontSize: 64, mb: 1 }} />
          <Typography variant="h6" fontWeight={600}>
            Something went wrong
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 3, maxWidth: 420 }}>
            An unexpected error occurred while rendering this page. Reloading usually fixes it.
          </Typography>
          <Button variant="contained" startIcon={<RefreshRoundedIcon />} onClick={() => window.location.reload()}>
            Reload Page
          </Button>
        </Box>
      )
    }
    return this.props.children
  }
}

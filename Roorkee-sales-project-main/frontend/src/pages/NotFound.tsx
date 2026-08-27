import { Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { FullPageMessage } from '../components/common/FullPageMessage'

export default function NotFound() {
  const navigate = useNavigate()
  return (
    <FullPageMessage
      visual={
        <Typography variant="h1" fontWeight={800} color="primary.main" sx={{ fontSize: { xs: 64, sm: 96 } }}>
          404
        </Typography>
      }
      title="Page not found"
      description="The page you're looking for doesn't exist or may have moved."
      actionLabel="Back to Dashboard"
      onAction={() => navigate('/')}
    />
  )
}

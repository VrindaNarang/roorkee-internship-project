import LockOutlinedIcon from '@mui/icons-material/LockOutlined'
import { useNavigate } from 'react-router-dom'
import { FullPageMessage } from '../components/common/FullPageMessage'

export default function Forbidden() {
  const navigate = useNavigate()
  return (
    <FullPageMessage
      visual={<LockOutlinedIcon color="error" sx={{ fontSize: 64 }} />}
      title="Access restricted"
      description="Your account role doesn't have permission to view this page. Contact an administrator if you believe this is a mistake."
      actionLabel="Back to Dashboard"
      onAction={() => navigate('/')}
    />
  )
}

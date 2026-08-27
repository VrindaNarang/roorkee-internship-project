import { Box, CircularProgress } from '@mui/material'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import type { UserRole } from '../../api/types'

interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
}

// Gates an entire route subtree (used once, wrapping <AppRoutes>'s
// protected <Route> group) rather than requiring every page to check auth
// itself. `allowedRoles` is optional — most pages are readable by any
// logged-in role; only a handful of admin-ish actions are role-restricted,
// and those are enforced at the component level (a disabled button) since
// the backend is the real authority there (see `app/auth/dependencies.py`).
export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <Box sx={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <CircularProgress aria-label="Checking session" />
      </Box>
    )
  }

  if (status === 'unauthenticated' || !user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/forbidden" replace />
  }

  return <Outlet />
}

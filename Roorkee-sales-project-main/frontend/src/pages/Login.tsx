import { useState } from 'react'
import type { FormEvent } from 'react'
import {
  Alert,
  Box,
  Button,
  IconButton,
  InputAdornment,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import { alpha } from '@mui/material/styles'
import { isAxiosError } from 'axios'
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined'
import VisibilityRoundedIcon from '@mui/icons-material/VisibilityRounded'
import VisibilityOffRoundedIcon from '@mui/icons-material/VisibilityOffRounded'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const DEMO_ACCOUNTS = [
  { role: 'Admin', email: 'admin@salespilot.example.com' },
  { role: 'Sales Manager', email: 'manager@salespilot.example.com' },
  { role: 'Sales Executive', email: 'executive@salespilot.example.com' },
]
const DEMO_PASSWORD = 'ChangeMe123!'

// Distinguishes a genuine bad-credentials response (401) from every other
// failure (backend unreachable, CORS misconfigured, 5xx, timeout) — showing
// "Incorrect email or password" for all of them would be actively
// misleading when the account/password were actually fine.
function describeLoginError(err: unknown): string {
  if (isAxiosError(err)) {
    if (!err.response) {
      return "Can't reach the server. Check your connection and that the API is running, then try again."
    }
    if (err.response.status === 401) {
      return 'Incorrect email or password.'
    }
    const detail = err.response.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    return 'Something went wrong while signing in. Please try again.'
  }
  return 'Something went wrong while signing in. Please try again.'
}

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email.trim(), password)
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setError(describeLoginError(err))
    } finally {
      setSubmitting(false)
    }
  }

  const fillDemoAccount = (demoEmail: string) => {
    setEmail(demoEmail)
    setPassword(DEMO_PASSWORD)
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: 'background.default',
        p: 2,
      }}
    >
      <Paper
        component="form"
        onSubmit={handleSubmit}
        variant="outlined"
        sx={{ width: '100%', maxWidth: 400, p: { xs: 3, sm: 4.5 } }}
      >
        <Stack alignItems="center" spacing={1.5} sx={{ mb: 3.5, textAlign: 'center' }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 44,
              height: 44,
              borderRadius: 3,
              bgcolor: 'primary.main',
              color: 'primary.contrastText',
            }}
          >
            <ScienceOutlinedIcon fontSize="medium" />
          </Box>
          <Box>
            <Typography variant="h6" fontWeight={700}>
              SalesPilot AI
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Sign in to your account
            </Typography>
          </Box>
        </Stack>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Stack spacing={2}>
          <TextField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
            fullWidth
            autoComplete="username"
            slotProps={{ htmlInput: { 'aria-label': 'Email address' } }}
          />
          <TextField
            label="Password"
            type={showPassword ? 'text' : 'password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            fullWidth
            autoComplete="current-password"
            slotProps={{
              htmlInput: { 'aria-label': 'Password' },
              input: {
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={() => setShowPassword((v) => !v)}
                      edge="end"
                      size="small"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                    >
                      {showPassword ? <VisibilityOffRoundedIcon fontSize="small" /> : <VisibilityRoundedIcon fontSize="small" />}
                    </IconButton>
                  </InputAdornment>
                ),
              },
            }}
          />
          <Button type="submit" variant="contained" size="large" disabled={submitting} fullWidth>
            {submitting ? 'Signing in…' : 'Sign In'}
          </Button>
        </Stack>

        <Box sx={{ mt: 3.5, pt: 2.5, borderTop: '1px solid', borderColor: 'divider' }}>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.25 }}>
            Demo accounts (password: {DEMO_PASSWORD}) — click to fill in:
          </Typography>
          <Stack spacing={0.75}>
            {DEMO_ACCOUNTS.map((account) => (
              <Button
                key={account.email}
                variant="text"
                onClick={() => fillDemoAccount(account.email)}
                sx={{
                  justifyContent: 'flex-start',
                  textAlign: 'left',
                  color: 'text.primary',
                  px: 1.25,
                  py: 0.75,
                  borderRadius: 2.5,
                  bgcolor: (t) => alpha(t.palette.text.primary, t.palette.mode === 'light' ? 0.03 : 0.05),
                  '&:hover': {
                    bgcolor: (t) => alpha(t.palette.primary.main, t.palette.mode === 'light' ? 0.08 : 0.16),
                  },
                }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="caption" component="span" fontWeight={700}>
                    {account.role}
                  </Typography>
                  <Typography variant="caption" component="span" color="text.secondary">
                    {' '}
                    — {account.email}
                  </Typography>
                </Box>
              </Button>
            ))}
          </Stack>
        </Box>
      </Paper>
    </Box>
  )
}

import { Avatar, Box, Chip, Divider, FormControlLabel, Stack, Switch, Typography } from '@mui/material'
import { useAuth } from '../context/AuthContext'
import { useThemeMode } from '../context/ThemeModeContext'
import { PageIntro } from '../components/common/PageIntro'
import { SectionCard } from '../components/common/SectionCard'
import { formatDate } from '../utils/format'

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  sales_manager: 'Sales Manager',
  sales_executive: 'Sales Executive',
}

function initialsFor(name: string) {
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')
}

export default function Settings() {
  const { mode, toggleMode } = useThemeMode()
  const { user } = useAuth()

  return (
    <>
      <PageIntro description="Account, appearance, and notification preferences." />

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2.5 }}>
        <SectionCard title="Profile">
          <Stack direction="row" spacing={2} alignItems="center">
            <Avatar sx={{ width: 48, height: 48, bgcolor: 'primary.main' }}>
              {user ? initialsFor(user.full_name) : '?'}
            </Avatar>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle2" fontWeight={600} noWrap>
                {user?.full_name}
              </Typography>
              <Typography variant="body2" color="text.secondary" noWrap>
                {user?.email}
              </Typography>
              {user && (
                <Chip label={ROLE_LABELS[user.role] ?? user.role} size="small" color="primary" sx={{ mt: 0.75 }} />
              )}
            </Box>
          </Stack>
          {user && (
            <>
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2" color="text.secondary">
                  Account created
                </Typography>
                <Typography variant="body2" fontWeight={600}>
                  {formatDate(user.created_at)}
                </Typography>
              </Box>
            </>
          )}
        </SectionCard>

        <SectionCard title="Appearance">
          <FormControlLabel
            control={<Switch checked={mode === 'dark'} onChange={toggleMode} />}
            label="Dark mode"
          />
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
            Applies across the whole app and is remembered on this device.
          </Typography>
        </SectionCard>

        <SectionCard title="Notifications">
          <FormControlLabel control={<Switch checked disabled />} label="Email notifications" />
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
            Notification preferences aren't configurable yet.
          </Typography>
        </SectionCard>

        <SectionCard title="About">
          <Stack spacing={1}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Version
              </Typography>
              <Typography variant="body2" fontWeight={600}>
                1.0.0
              </Typography>
            </Box>
            <Divider />
            <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
              <Typography variant="body2" color="text.secondary">
                Build
              </Typography>
              <Typography variant="body2" fontWeight={600}>
                Milestone 11 — Enterprise Production Readiness
              </Typography>
            </Box>
          </Stack>
        </SectionCard>
      </Box>
    </>
  )
}

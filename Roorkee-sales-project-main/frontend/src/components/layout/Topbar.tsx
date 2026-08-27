import { useState } from 'react'
import {
  AppBar,
  Avatar,
  Box,
  Chip,
  Divider,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Tooltip,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { useTheme } from '@mui/material/styles'
import MenuRoundedIcon from '@mui/icons-material/MenuRounded'
import NotificationsNoneOutlinedIcon from '@mui/icons-material/NotificationsNoneOutlined'
import Brightness4RoundedIcon from '@mui/icons-material/Brightness4Rounded'
import Brightness7RoundedIcon from '@mui/icons-material/Brightness7Rounded'
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined'
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useThemeMode } from '../../context/ThemeModeContext'
import { SearchInput } from '../filters/SearchInput'
import { SIDEBAR_WIDTH } from './Sidebar'

const PAGE_TITLES: { match: (path: string) => boolean; title: string }[] = [
  { match: (p) => p === '/', title: 'Dashboard' },
  { match: (p) => p === '/customers', title: 'Customers' },
  { match: (p) => /^\/customers\/.+/.test(p), title: 'Customer Profile' },
  { match: (p) => p === '/products', title: 'Products' },
  { match: (p) => /^\/products\/.+/.test(p), title: 'Product Details' },
  { match: (p) => p === '/analytics', title: 'Analytics' },
  { match: (p) => p === '/sales-opportunities', title: 'Sales Opportunities' },
  { match: (p) => p === '/recommendations', title: 'Recommendations' },
  { match: (p) => p === '/settings', title: 'Settings' },
]

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  sales_manager: 'Sales Manager',
  sales_executive: 'Sales Executive',
}

interface TopbarProps {
  onMenuClick: () => void
}

function initialsFor(name: string) {
  const parts = name.trim().split(/\s+/)
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')
}

export function Topbar({ onMenuClick }: TopbarProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const theme = useTheme()
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'))
  const { mode, toggleMode } = useThemeMode()
  const { user, logout } = useAuth()
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const [search, setSearch] = useState('')

  const title = PAGE_TITLES.find((entry) => entry.match(location.pathname))?.title ?? 'SalesPilot AI'

  const handleSearch = (value: string) => {
    setSearch(value)
    if (value.trim()) {
      navigate(`/customers?search=${encodeURIComponent(value.trim())}`)
    }
  }

  const handleLogout = () => {
    setAnchorEl(null)
    logout()
    navigate('/login', { replace: true })
  }

  return (
    <AppBar
      position="fixed"
      color="inherit"
      sx={{
        width: isDesktop ? `calc(100% - ${SIDEBAR_WIDTH}px)` : '100%',
        ml: isDesktop ? `${SIDEBAR_WIDTH}px` : 0,
        backgroundColor: 'background.paper',
      }}
    >
      <Toolbar sx={{ display: 'flex', gap: 2, justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 0 }}>
          {!isDesktop && (
            <IconButton onClick={onMenuClick} edge="start" aria-label="Open navigation menu">
              <MenuRoundedIcon />
            </IconButton>
          )}
          <Typography variant="h6" fontWeight={600} noWrap component="h1">
            {title}
          </Typography>
        </Box>

        <Box sx={{ flexGrow: 1, maxWidth: 360, display: { xs: 'none', sm: 'block' } }}>
          <SearchInput
            value={search}
            onChange={handleSearch}
            placeholder="Search customers…"
            fullWidth
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 999,
                bgcolor: (t) => (t.palette.mode === 'light' ? 'rgba(17, 24, 39, 0.035)' : 'rgba(255, 255, 255, 0.06)'),
                '& fieldset': { borderColor: 'transparent' },
                '&:hover fieldset': { borderColor: 'divider' },
                '&.Mui-focused fieldset': { borderColor: 'primary.main' },
              },
            }}
          />
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Tooltip title={mode === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}>
            <IconButton onClick={toggleMode} aria-label="Toggle color mode">
              {mode === 'light' ? <Brightness4RoundedIcon /> : <Brightness7RoundedIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Notifications (coming soon)">
            <IconButton aria-label="Notifications">
              <NotificationsNoneOutlinedIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title={user ? `${user.full_name} — ${ROLE_LABELS[user.role] ?? user.role}` : 'Account menu'}>
            <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} sx={{ ml: 0.5 }} aria-label="Account menu">
              <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14 }}>
                {user ? initialsFor(user.full_name) : '?'}
              </Avatar>
            </IconButton>
          </Tooltip>
          <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
            <Box sx={{ px: 2, py: 1, minWidth: 220 }}>
              <Typography variant="subtitle2" fontWeight={600} noWrap>
                {user?.full_name ?? 'Unknown user'}
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block" noWrap>
                {user?.email}
              </Typography>
              {user && (
                <Chip
                  label={ROLE_LABELS[user.role] ?? user.role}
                  size="small"
                  color="primary"
                  variant="outlined"
                  sx={{ mt: 0.75 }}
                />
              )}
            </Box>
            <Divider />
            <MenuItem
              onClick={() => {
                setAnchorEl(null)
                navigate('/settings')
              }}
            >
              <ListItemIcon>
                <SettingsOutlinedIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Settings</ListItemText>
            </MenuItem>
            <Divider />
            <MenuItem onClick={handleLogout}>
              <ListItemIcon>
                <LogoutRoundedIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Log out</ListItemText>
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  )
}

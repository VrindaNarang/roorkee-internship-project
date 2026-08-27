import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  useMediaQuery,
} from '@mui/material'
import { alpha, useTheme } from '@mui/material/styles'
import DashboardOutlinedIcon from '@mui/icons-material/DashboardOutlined'
import PeopleAltOutlinedIcon from '@mui/icons-material/PeopleAltOutlined'
import Inventory2OutlinedIcon from '@mui/icons-material/Inventory2Outlined'
import InsightsOutlinedIcon from '@mui/icons-material/InsightsOutlined'
import TrendingUpRoundedIcon from '@mui/icons-material/TrendingUpRounded'
import RecommendRoundedIcon from '@mui/icons-material/RecommendRounded'
import SettingsOutlinedIcon from '@mui/icons-material/SettingsOutlined'
import ScienceOutlinedIcon from '@mui/icons-material/ScienceOutlined'
import { useLocation, useNavigate } from 'react-router-dom'

export const SIDEBAR_WIDTH = 240

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: <DashboardOutlinedIcon /> },
  { label: 'Customers', path: '/customers', icon: <PeopleAltOutlinedIcon /> },
  { label: 'Products', path: '/products', icon: <Inventory2OutlinedIcon /> },
  { label: 'Analytics', path: '/analytics', icon: <InsightsOutlinedIcon /> },
  { label: 'Sales Opportunities', path: '/sales-opportunities', icon: <TrendingUpRoundedIcon /> },
  { label: 'Recommendations', path: '/recommendations', icon: <RecommendRoundedIcon /> },
  { label: 'Settings', path: '/settings', icon: <SettingsOutlinedIcon /> },
]

function isActive(pathname: string, itemPath: string) {
  if (itemPath === '/') return pathname === '/'
  return pathname === itemPath || pathname.startsWith(`${itemPath}/`)
}

interface SidebarProps {
  mobileOpen: boolean
  onClose: () => void
}

export function Sidebar({ mobileOpen, onClose }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const theme = useTheme()
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'))

  const content = (
    <>
      <Toolbar sx={{ display: 'flex', alignItems: 'center', gap: 1.25, px: 2.5 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 32,
            height: 32,
            borderRadius: 2,
            bgcolor: 'primary.main',
            color: 'primary.contrastText',
            flexShrink: 0,
          }}
        >
          <ScienceOutlinedIcon sx={{ fontSize: 19 }} />
        </Box>
        <Typography variant="h6" noWrap fontWeight={700} sx={{ fontSize: 16, letterSpacing: '-0.01em' }}>
          SalesPilot AI
        </Typography>
      </Toolbar>
      <Box sx={{ overflow: 'auto', px: 1.5, py: 1 }}>
        <List sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          {NAV_ITEMS.map((item) => {
            const selected = isActive(location.pathname, item.path)
            return (
              <ListItemButton
                key={item.path}
                selected={selected}
                onClick={() => {
                  navigate(item.path)
                  if (!isDesktop) onClose()
                }}
                sx={{
                  borderRadius: 2.5,
                  py: 1,
                  color: 'text.secondary',
                  '&:hover': {
                    backgroundColor: (t) => alpha(t.palette.text.primary, t.palette.mode === 'light' ? 0.04 : 0.06),
                  },
                  '&.Mui-selected': {
                    backgroundColor: (t) => alpha(t.palette.primary.main, t.palette.mode === 'light' ? 0.1 : 0.18),
                    color: 'primary.main',
                    '& .MuiListItemIcon-root': { color: 'primary.main' },
                    '&:hover': {
                      backgroundColor: (t) => alpha(t.palette.primary.main, t.palette.mode === 'light' ? 0.14 : 0.22),
                    },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 34, color: 'inherit' }}>{item.icon}</ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{ fontSize: 14, fontWeight: selected ? 600 : 500 }}
                />
              </ListItemButton>
            )
          })}
        </List>
      </Box>
    </>
  )

  if (isDesktop) {
    return (
      <Drawer
        variant="permanent"
        sx={{
          width: SIDEBAR_WIDTH,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: SIDEBAR_WIDTH,
            boxSizing: 'border-box',
            backgroundColor: 'background.paper',
          },
        }}
      >
        {content}
      </Drawer>
    )
  }

  return (
    <Drawer
      variant="temporary"
      open={mobileOpen}
      onClose={onClose}
      ModalProps={{ keepMounted: true }}
      sx={{
        [`& .MuiDrawer-paper`]: {
          width: SIDEBAR_WIDTH,
          boxSizing: 'border-box',
          backgroundColor: 'background.paper',
        },
      }}
    >
      {content}
    </Drawer>
  )
}

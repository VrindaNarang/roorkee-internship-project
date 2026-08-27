import { useState } from 'react'
import { Box, Toolbar } from '@mui/material'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'

// Top-level app shell: fixed sidebar + topbar, scrollable content area.
// Page components are rendered via <Outlet /> from React Router.
export function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <Box sx={{ display: 'flex' }}>
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <Topbar onMenuClick={() => setMobileOpen(true)} />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          minHeight: '100vh',
          minWidth: 0,
          backgroundColor: 'background.default',
          p: { xs: 2, sm: 3, lg: 4 },
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  )
}

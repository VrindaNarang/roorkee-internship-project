import { lazy, Suspense } from 'react'
import { Box, CircularProgress } from '@mui/material'
import { Route, Routes } from 'react-router-dom'
import { Layout } from '../components/layout/Layout'
import { ProtectedRoute } from '../components/auth/ProtectedRoute'
import Login from '../pages/Login'
import Forbidden from '../pages/Forbidden'
import NotFound from '../pages/NotFound'

// Route-level code splitting: each page ships as its own chunk, fetched on
// first navigation rather than bundled into the initial load — the app
// shell (Login, Layout, auth machinery) still loads eagerly since it's
// needed immediately, but a first-time visitor to /dashboard never
// downloads the Recommendations/Analytics/Copilot bundles until they
// actually navigate there.
const Dashboard = lazy(() => import('../pages/Dashboard'))
const Customers = lazy(() => import('../pages/Customers'))
const CustomerDetail = lazy(() => import('../pages/CustomerDetail'))
const Products = lazy(() => import('../pages/Products'))
const ProductDetail = lazy(() => import('../pages/ProductDetail'))
const Analytics = lazy(() => import('../pages/Analytics'))
const SalesOpportunities = lazy(() => import('../pages/SalesOpportunities'))
const Recommendations = lazy(() => import('../pages/Recommendations'))
const Settings = lazy(() => import('../pages/Settings'))

function RouteFallback() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
      <CircularProgress aria-label="Loading page" />
    </Box>
  )
}

export function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/forbidden" element={<Forbidden />} />

        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/customers/:id" element={<CustomerDetail />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:id" element={<ProductDetail />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/sales-opportunities" element={<SalesOpportunities />} />
            <Route path="/recommendations" element={<Recommendations />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  )
}

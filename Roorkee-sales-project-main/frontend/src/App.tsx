import { BrowserRouter } from 'react-router-dom'
import { ErrorBoundary } from './components/common/ErrorBoundary'
import { AuthProvider } from './context/AuthContext'
import { ThemeModeProvider } from './context/ThemeModeContext'
import { AppRoutes } from './routes/AppRoutes'

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeModeProvider>
        <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </BrowserRouter>
      </ThemeModeProvider>
    </ErrorBoundary>
  )
}

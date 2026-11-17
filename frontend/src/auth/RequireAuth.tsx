import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider'

/** Routes inside need a signed-in user; others are sent to /login and brought back afterwards. */
export function RequireAuth() {
  const { token } = useAuth()
  const location = useLocation()
  if (!token) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  return <Outlet />
}

/** Public pages (landing, sign in) skip straight to the app when already signed in. */
export function RedirectIfSignedIn() {
  const { token } = useAuth()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  if (token) return <Navigate to={from && from !== '/login' ? from : '/overview'} replace />
  return <Outlet />
}

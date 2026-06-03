import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div
        className="min-h-screen bg-white flex items-center justify-center"
        role="status"
        aria-live="polite"
        aria-label="Loading..."
      >
        <div className="w-6 h-6 border-2 border-brand-dark border-t-transparent rounded-full animate-spin" />
        <span className="sr-only">Loading...</span>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Outlet />
}

import { useLayoutEffect } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import { Landing } from './pages/Landing'
import { Pricing } from './pages/Pricing'
import { About } from './pages/About'
import { Terms } from './pages/Terms'
import { Privacy } from './pages/Privacy'
import { Login } from './pages/Login'
import { SignUp } from './pages/SignUp'
import { Chat } from './pages/Chat'
import { ProtectedRoute } from './routes/ProtectedRoute'
import { PublicOnlyRoute } from './routes/PublicOnlyRoute'
import { useThemeSync } from './hooks/useTheme'

function ScrollToTop() {
  const { pathname } = useLocation()

  useLayoutEffect(() => {
    if (!pathname.startsWith('/chat')) {
      window.scrollTo({ top: 0, left: 0 })
    }
  }, [pathname])

  return null
}

export default function App() {
  useThemeSync()

  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/about" element={<About />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/privacy" element={<Privacy />} />

        <Route element={<PublicOnlyRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<SignUp />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="/chat" element={<Chat />} />
          <Route path="/chat/:chatId" element={<Chat />} />
        </Route>
      </Routes>
    </>
  )
}

import { Routes, Route } from 'react-router-dom'
import { Landing } from './pages/Landing'
import { Pricing } from './pages/Pricing'
import { About } from './pages/About'
import { Login } from './pages/Login'
import { SignUp } from './pages/SignUp'
import { Chat } from './pages/Chat'
import { ProtectedRoute } from './routes/ProtectedRoute'
import { PublicOnlyRoute } from './routes/PublicOnlyRoute'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/pricing" element={<Pricing />} />
      <Route path="/about" element={<About />} />

      <Route element={<PublicOnlyRoute />}>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<SignUp />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/chat" element={<Chat />} />
        <Route path="/chat/:chatId" element={<Chat />} />
      </Route>
    </Routes>
  )
}
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import Pricing from './pages/Pricing'
import About from './pages/About'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/about" element={<About />} />
        <Route path="/login" element={<div>Login — built in Chat 7</div>} />
        <Route path="/signup" element={<div>SignUp — built in Chat 7</div>} />
        <Route path="/chat" element={<div>Chat — built in Chat 8</div>} />
        <Route path="/chat/:chatId" element={<div>Chat — built in Chat 8</div>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import Button from '../ui/Button'

function Navbar() {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  const navLinks = [
    { label: 'Home', path: '/' },
    { label: 'Pricing', path: '/pricing' },
    { label: 'About', path: '/about' },
  ]

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname === path
  }

  return (
    <nav className="w-full bg-white px-6 py-4 flex items-center justify-between border-b border-gray-200 relative">
      <Link to="/" className="text-brand-dark font-extrabold text-lg tracking-wide">
        DevSelect
      </Link>

      <div className="hidden md:flex items-center gap-8">
        {navLinks.map((link) => (
          <Link
            key={link.path}
            to={link.path}
            className={`text-ui text-brand-dark transition-all duration-200 hover:text-brand-muted pb-1 ${
              isActive(link.path)
                ? 'border-b-2 border-brand-dark font-semibold'
                : 'border-b-2 border-transparent'
            }`}
          >
            {link.label}
          </Link>
        ))}
      </div>

      <div className="hidden md:flex items-center gap-4">
        <Link to="/login" className="text-ui text-brand-dark hover:text-brand-muted transition-all duration-200">
          Login
        </Link>
        <Link to="/signup">
          <Button variant="primary" size="sm">
            Get Started
          </Button>
        </Link>
      </div>

      <button
        onClick={() => setMenuOpen(!menuOpen)}
        className="md:hidden text-brand-dark p-1"
        aria-label="Toggle menu"
      >
        {menuOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {menuOpen && (
        <div className="absolute top-full left-0 right-0 bg-white border-b border-gray-200 flex flex-col px-6 py-4 gap-4 md:hidden z-50 shadow-card">
          {navLinks.map((link) => (
            <Link
              key={link.path}
              to={link.path}
              onClick={() => setMenuOpen(false)}
              className={`text-ui text-brand-dark py-2 transition-all duration-200 hover:text-brand-muted ${
                isActive(link.path) ? 'font-semibold' : ''
              }`}
            >
              {link.label}
            </Link>
          ))}
          <div className="flex flex-col gap-3 pt-2 border-t border-gray-100">
            <Link
              to="/login"
              onClick={() => setMenuOpen(false)}
              className="text-ui text-brand-dark hover:text-brand-muted transition-all duration-200 py-2"
            >
              Login
            </Link>
            <Link to="/signup" onClick={() => setMenuOpen(false)}>
              <Button variant="primary" size="sm" className="w-full">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      )}
    </nav>
  )
}

export default Navbar
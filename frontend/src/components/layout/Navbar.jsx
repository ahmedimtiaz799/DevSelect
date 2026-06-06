import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import Button from '../ui/Button'

const baseLinkClass =
  'text-ui transition-colors duration-200 rounded-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-focusRing/70 focus-visible:ring-offset-2 focus-visible:ring-offset-white'
const desktopLinkClass =
  `${baseLinkClass} pb-1 border-b-2`
const mobileLinkClass =
  `${baseLinkClass} py-2`

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
      <Link
        to="/"
        className="text-brand-dark font-extrabold text-lg tracking-wide rounded-sm transition-colors duration-200 hover:text-brand-secondary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-focusRing/70 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
      >
        DevSelect
      </Link>

      <div className="hidden md:flex items-center gap-8">
        {navLinks.map((link) => {
          const active = isActive(link.path)

          return (
            <Link
              key={link.path}
              to={link.path}
              aria-current={active ? 'page' : undefined}
              className={`${desktopLinkClass} ${
                active
                  ? 'text-brand-dark border-brand-dark font-semibold'
                  : 'text-brand-secondary border-transparent hover:text-brand-dark'
              }`}
            >
              {link.label}
            </Link>
          )
        })}
      </div>

      <div className="hidden md:flex items-center gap-4">
        <Link
          to="/login"
          className={`${baseLinkClass} text-brand-secondary hover:text-brand-dark`}
        >
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
        className="md:hidden text-brand-dark p-1 rounded-md transition-colors duration-200 hover:text-brand-secondary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-focusRing/70 focus-visible:ring-offset-2 focus-visible:ring-offset-white"
        aria-label="Toggle menu"
      >
        {menuOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      {menuOpen && (
        <div className="absolute top-full left-0 right-0 bg-white border-b border-gray-200 flex flex-col px-6 py-4 gap-4 md:hidden z-50 shadow-card">
          {navLinks.map((link) => {
            const active = isActive(link.path)

            return (
              <Link
                key={link.path}
                to={link.path}
                aria-current={active ? 'page' : undefined}
                onClick={() => setMenuOpen(false)}
                className={`${mobileLinkClass} ${
                  active
                    ? 'text-brand-dark font-semibold'
                    : 'text-brand-secondary hover:text-brand-dark'
                }`}
              >
                {link.label}
              </Link>
            )
          })}
          <div className="flex flex-col gap-3 pt-2 border-t border-gray-100">
            <Link
              to="/login"
              onClick={() => setMenuOpen(false)}
              className={`${mobileLinkClass} text-brand-secondary hover:text-brand-dark`}
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

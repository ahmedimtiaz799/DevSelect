import { Link, useLocation } from 'react-router-dom'
import Button from '../ui/Button'

function Navbar() {
  const location = useLocation()

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
    <nav className="w-full bg-white px-8 py-4 flex items-center justify-between border-b border-gray-200">
      <Link to="/" className="text-brand-dark font-extrabold text-lg tracking-wide">
        DevSelect
      </Link>
      <div className="flex items-center gap-8">
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
      <div className="flex items-center gap-4">
        <Link to="/login" className="text-ui text-brand-dark hover:text-brand-muted transition-all duration-200">
          Login
        </Link>
        <Link to="/signup">
          <Button variant="primary" size="sm">
            Get Started
          </Button>
        </Link>
      </div>
    </nav>
  )
}

export default Navbar
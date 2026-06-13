import { useEffect, useRef, useState } from 'react'
import { Check, LogOut, Moon, Sun } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { getAuthProfileDisplay } from '../../lib/authProfile'

function getFirstName(displayName) {
  if (!displayName) return 'User'

  return displayName.trim().split(' ')[0]
}

function getSavedTheme() {
  try {
    return localStorage.getItem('devselect-theme') || 'light'
  } catch {
    return 'light'
  }
}

export function UserMenu({ isCollapsed, labelsVisible = true }) {
  const { user, signOut } = useAuth()

  const [open, setOpen] = useState(false)
  const [theme, setTheme] = useState(getSavedTheme)

  const menuRef = useRef(null)

  const { displayName, subtitle, avatarInitial, avatarUrl } =
    getAuthProfileDisplay(user)
  const firstName = getFirstName(displayName)

  useEffect(() => {
    function handleOutsideClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false)
      }
    }

    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handleOutsideClick)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handleOutsideClick)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem('devselect-theme', theme)
    } catch {
      // Ignore localStorage errors
    }

    document.documentElement.classList.toggle('dark', theme === 'dark')
  }, [theme])

  function handleThemeChange(nextTheme) {
    setTheme(nextTheme)
  }

  return (
    <div ref={menuRef} className="relative w-full">
      {open && (
        <div
          className={`absolute bottom-full mb-3 w-60 rounded-2xl bg-ds-sidebar border border-white/15 shadow-xl overflow-hidden z-[9999] ${
            isCollapsed ? 'left-0' : 'left-0'
          }`}
        >
          <div className="px-4 py-3">
            <p className="text-sm font-semibold text-ds-text-inverse truncate">
              {displayName}
            </p>

            {subtitle && (
              <p className="text-xs text-white/50 truncate mt-0.5">
                {subtitle}
              </p>
            )}
          </div>

          <div className="h-px bg-white/10" />

          <div className="px-2 py-2">
            <div className="px-2 pb-1">
              <p className="text-[10px] uppercase tracking-widest text-white/50 font-bold">
                Theme
              </p>
            </div>

            <button
              onClick={() => handleThemeChange('light')}
              className="flex items-center justify-between w-full px-3 py-2 rounded-lg text-sm text-white/80 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 focus-visible:ring-inset"
            >
              <span className="flex items-center gap-3">
                <Sun size={15} className="text-white/50" />
                Light
              </span>

              {theme === 'light' && (
                <Check size={15} className="text-white/80" />
              )}
            </button>

            <button
              onClick={() => handleThemeChange('dark')}
              className="flex items-center justify-between w-full px-3 py-2 rounded-lg text-sm text-white/80 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 focus-visible:ring-inset"
            >
              <span className="flex items-center gap-3">
                <Moon size={15} className="text-white/50" />
                Dark
              </span>

              {theme === 'dark' && (
                <Check size={15} className="text-white/80" />
              )}
            </button>
          </div>

          <div className="h-px bg-white/10" />

          <div className="p-2">
            <button
              onClick={signOut}
              className="flex items-center gap-3 w-full px-3 py-2 rounded-lg text-sm text-red-400 hover:text-red-300 hover:bg-red-500/15 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 focus-visible:ring-inset"
            >
              <LogOut size={15} />
              Log out
            </button>
          </div>
        </div>
      )}

      <button
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Open user menu"
        className={`w-full min-h-[48px] flex items-center rounded-xl transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 ${
          isCollapsed ? 'justify-center p-2' : 'gap-3 px-2 py-2'
        }`}
        title={isCollapsed ? displayName : undefined}
      >
        <div className="flex items-center justify-center w-9 h-9 rounded-full bg-ds-text-inverse text-ds-text-strong text-sm font-extrabold shrink-0">
          {avatarUrl ? (
            <img
              src={avatarUrl}
              alt=""
              referrerPolicy="no-referrer"
              className="w-full h-full rounded-full object-cover"
            />
          ) : (
            avatarInitial
          )}
        </div>

        {!isCollapsed && (
          <p
            className={`overflow-hidden whitespace-nowrap text-sm leading-none font-semibold text-ds-text-inverse truncate max-w-[150px] text-left transition-opacity duration-150 ${
              labelsVisible ? 'opacity-100' : 'opacity-0'
            }`}
          >
            {firstName}
          </p>
        )}
      </button>
    </div>
  )
}

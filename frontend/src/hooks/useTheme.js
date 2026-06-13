import { useCallback, useEffect, useState } from 'react'

const THEME_STORAGE_KEY = 'devselect-theme'
const THEME_CHANGE_EVENT = 'devselect-theme-change'
const SYSTEM_THEME_QUERY = '(prefers-color-scheme: dark)'
const THEME_CHOICES = new Set(['system', 'light', 'dark'])

function normalizeThemeChoice(value) {
  return THEME_CHOICES.has(value) ? value : 'system'
}

function getSystemTheme() {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light'

  return window.matchMedia(SYSTEM_THEME_QUERY).matches ? 'dark' : 'light'
}

function resolveTheme(themeChoice) {
  const normalizedChoice = normalizeThemeChoice(themeChoice)

  return normalizedChoice === 'system'
    ? getSystemTheme()
    : normalizedChoice
}

function readStoredThemeChoice() {
  try {
    return normalizeThemeChoice(localStorage.getItem(THEME_STORAGE_KEY))
  } catch {
    return 'system'
  }
}

function writeStoredThemeChoice(themeChoice) {
  const normalizedChoice = normalizeThemeChoice(themeChoice)

  try {
    localStorage.setItem(THEME_STORAGE_KEY, normalizedChoice)
  } catch {
    // Ignore localStorage errors.
  }

  return normalizedChoice
}

function applyTheme(themeChoice) {
  const normalizedChoice = normalizeThemeChoice(themeChoice)
  const resolvedTheme = resolveTheme(normalizedChoice)

  document.documentElement.setAttribute('data-theme', resolvedTheme)
  document.documentElement.setAttribute('data-theme-choice', normalizedChoice)

  return resolvedTheme
}

function notifyThemeChange(themeChoice) {
  window.dispatchEvent(
    new CustomEvent(THEME_CHANGE_EVENT, {
      detail: { themeChoice },
    })
  )
}

export function useTheme() {
  const [themeChoice, setThemeChoiceState] = useState(readStoredThemeChoice)
  const [systemTheme, setSystemTheme] = useState(getSystemTheme)
  const resolvedTheme =
    themeChoice === 'system' ? systemTheme : themeChoice

  useEffect(() => {
    writeStoredThemeChoice(themeChoice)
    applyTheme(themeChoice)

    function handleThemeChange(event) {
      const nextChoice = normalizeThemeChoice(event.detail?.themeChoice)
      setThemeChoiceState(nextChoice)
      applyTheme(nextChoice)
    }

    function handleStorageChange(event) {
      if (event.key !== THEME_STORAGE_KEY) return

      const nextChoice = readStoredThemeChoice()
      setThemeChoiceState(nextChoice)
      applyTheme(nextChoice)
    }

    function handleSystemThemeChange(event) {
      const nextSystemTheme = event.matches ? 'dark' : 'light'
      setSystemTheme(nextSystemTheme)

      if (readStoredThemeChoice() === 'system') {
        applyTheme('system')
      }
    }

    const mediaQuery = window.matchMedia?.(SYSTEM_THEME_QUERY)

    window.addEventListener(THEME_CHANGE_EVENT, handleThemeChange)
    window.addEventListener('storage', handleStorageChange)
    if (mediaQuery?.addEventListener) {
      mediaQuery.addEventListener('change', handleSystemThemeChange)
    } else {
      mediaQuery?.addListener?.(handleSystemThemeChange)
    }

    return () => {
      window.removeEventListener(THEME_CHANGE_EVENT, handleThemeChange)
      window.removeEventListener('storage', handleStorageChange)
      if (mediaQuery?.removeEventListener) {
        mediaQuery.removeEventListener('change', handleSystemThemeChange)
      } else {
        mediaQuery?.removeListener?.(handleSystemThemeChange)
      }
    }
  }, [themeChoice])

  const setThemeChoice = useCallback((nextThemeChoice) => {
    const normalizedChoice = writeStoredThemeChoice(nextThemeChoice)
    setThemeChoiceState(normalizedChoice)
    applyTheme(normalizedChoice)
    notifyThemeChange(normalizedChoice)
  }, [])

  return {
    themeChoice,
    resolvedTheme,
    setThemeChoice,
  }
}

export function useThemeSync() {
  useTheme()
}

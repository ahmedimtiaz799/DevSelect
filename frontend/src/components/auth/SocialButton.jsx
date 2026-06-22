import { supabase } from '../../lib/supabase'
import { getAuthErrorMessage } from '../../lib/authErrors'

const DEBUG_AUTH_LOGS = import.meta.env.DEV

function logAuthWarning(error) {
  if (!DEBUG_AUTH_LOGS) return
  console.warn('Supabase OAuth sign-in failed', {
    code: error?.code ?? null,
    name: error?.name ?? null,
  })
}

export function SocialButton({ provider, label, icon, onError, primary }) {
  async function handleClick() {
    onError?.(null)

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/chat`,
        },
      })
      if (error) {
        logAuthWarning(error)
        onError?.(getAuthErrorMessage(error))
      }
    } catch (error) {
      logAuthWarning(error)
      onError?.(getAuthErrorMessage(error))
    }
  }

  return (
    <button
      onClick={handleClick}
      className={`flex items-center justify-center gap-3 w-full px-6 rounded-full border border-ds-button-secondary-border bg-ds-button-secondary text-ds-button-secondary-text text-sm font-medium transition-colors hover:bg-ds-button-secondary-hover focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-dsAlpha-focus-ring/70 focus-visible:ring-offset-1 focus-visible:ring-offset-ds-bg ${
        primary ? 'py-4 font-semibold' : 'py-3'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}

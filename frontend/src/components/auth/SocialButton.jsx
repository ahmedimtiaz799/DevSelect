import { supabase } from '../../lib/supabase'
import { getAuthErrorMessage } from '../../lib/authErrors'

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
        console.warn('Supabase OAuth sign-in failed:', error.message)
        onError?.(getAuthErrorMessage(error))
      }
    } catch (error) {
      console.warn('Supabase OAuth sign-in failed:', error?.message)
      onError?.(getAuthErrorMessage(error))
    }
  }

  return (
    <button
      onClick={handleClick}
      className={`flex items-center justify-center gap-3 w-full px-6 rounded-full text-white text-sm font-medium hover:opacity-90 transition-opacity bg-brand-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-focusRing focus-visible:ring-offset-2 focus-visible:ring-offset-white ${
        primary ? 'py-4 font-semibold' : 'py-3'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}

import { supabase } from '../../lib/supabase'

export function SocialButton({ provider, label, icon, onError, primary }) {
  async function handleClick() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/chat`,
      },
    })
    if (error) {
      onError?.(error.message)
    }
  }

  return (
    <button
      onClick={handleClick}
      className={`flex items-center justify-center gap-3 w-full px-6 rounded-full text-white text-sm font-medium hover:opacity-90 transition-opacity bg-brand-dark ${
        primary ? 'py-4 font-semibold' : 'py-3'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}
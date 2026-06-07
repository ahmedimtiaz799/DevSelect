import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

const listeners = new Set()
let authState = {
  user: null,
  session: null,
  loading: true,
}
let authInitialized = false

function emitAuthState(nextState) {
  authState = nextState
  listeners.forEach((listener) => listener(authState))
}

function ensureAuthInitialized() {
  if (authInitialized) return
  authInitialized = true

  supabase.auth.getSession().then(({ data: { session } }) => {
    emitAuthState({
      session,
      user: session?.user ?? null,
      loading: false,
    })
  })

  supabase.auth.onAuthStateChange((_event, session) => {
    emitAuthState({
      session,
      user: session?.user ?? null,
      loading: false,
    })
  })
}

export function useAuth() {
  const [state, setState] = useState(authState)

  useEffect(() => {
    ensureAuthInitialized()
    listeners.add(setState)

    return () => {
      listeners.delete(setState)
    }
  }, [])

  async function signOut() {
    await supabase.auth.signOut()
  }

  return { ...state, signOut }
}

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AuthLayout } from '../components/layout/AuthLayout'
import { SocialButton } from '../components/auth/SocialButton'
import { GitHubIcon } from '../components/auth/GitHubIcon'
import { GoogleIcon } from '../components/auth/GoogleIcon'

export function Login() {
  const [error, setError] = useState(null)

  return (
    <AuthLayout>
      <h1 className="text-2xl font-bold text-ds-text-strong text-center mb-8">
        Log in to DevSelect
      </h1>

      {error && (
        <p role="alert" className="text-ds-danger text-sm text-center -mb-2">{error}</p>
      )}

      <div className="w-full max-w-xs flex flex-col gap-3">
        <SocialButton
          provider="github"
          label="Continue with GitHub"
          icon={<GitHubIcon />}
          onError={setError}
          primary
        />
        <SocialButton
          provider="google"
          label="Continue with Google"
          icon={<GoogleIcon />}
          onError={setError}
        />
      </div>

      <p className="text-sm text-ds-text-muted mt-4">
        Don't have an account?{' '}
        <Link to="/signup" className="font-semibold text-ds-text-strong hover:underline">
          Sign up
        </Link>
      </p>

      <p className="text-xs text-ds-text-subtle text-center mt-4">
        By continuing, you agree to our{' '}
        <Link to="/terms" className="underline hover:text-ds-text-strong">Terms</Link>
        {' '}and{' '}
        <Link to="/privacy" className="underline hover:text-ds-text-strong">Privacy Policy</Link>
      </p>
    </AuthLayout>
  )
}

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { AuthLayout } from '../components/layout/AuthLayout'
import { SocialButton } from '../components/auth/SocialButton'
import { GitHubIcon } from '../components/auth/GitHubIcon'
import { GoogleIcon } from '../components/auth/GoogleIcon'

export function SignUp() {
  const [error, setError] = useState(null)

  return (
    <AuthLayout>
      <h1 className="text-2xl font-bold text-brand-dark text-center mb-8">
        Create your account
      </h1>

      {error && (
        <p role="alert" className="text-brand-error text-sm text-center -mb-2">{error}</p>
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

      <p className="text-sm text-gray-500 mt-4">
        Already have an account?{' '}
        <Link to="/login" className="font-semibold text-brand-dark hover:underline">
          Log in
        </Link>
      </p>

      <p className="text-xs text-gray-400 text-center mt-4">
        By continuing, you agree to our{' '}
        <Link to="/terms" className="underline hover:text-brand-dark">Terms</Link>
        {' '}and{' '}
        <Link to="/privacy" className="underline hover:text-brand-dark">Privacy Policy</Link>
      </p>
    </AuthLayout>
  )
}

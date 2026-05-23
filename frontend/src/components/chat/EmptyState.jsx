import { useAuth } from '../../hooks/useAuth'
import { CyclingTypewriter } from '../ui/CyclingTypewriter'

const PROMPTS = [
  'Upload a candidate CV to begin.',
  'Evaluates CVs and GitHub profiles in seconds.',
  'Supports all tech roles : engineers, designers, PMs.',
]

function getGreeting() {
  const hour = new Date().getHours()
  if (hour >= 5 && hour < 12) return 'Good morning'
  if (hour >= 12 && hour < 17) return 'Good afternoon'
  if (hour >= 17 && hour < 21) return 'Good evening'
  return 'Hello'
}

function getFirstName(user) {
  if (!user) return null

  const fullName = user.user_metadata?.full_name
  if (fullName) {
    const first = fullName.trim().split(' ')[0]
    return first.charAt(0).toUpperCase() + first.slice(1).toLowerCase()
  }

  const email = user.email
  if (email) {
    const part = email.split('@')[0].replace(/[^a-zA-Z]/g, '')
    if (!part) return null
    return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase()
  }

  return null
}

export function EmptyState() {
  const { user } = useAuth()
  const firstName = getFirstName(user)

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 text-center">
      <h2 className="text-display text-brand-dark mb-4">
        {getGreeting()}{firstName ? `, ${firstName}` : ''}
      </h2>
      <p className="text-body text-brand-muted">
        <CyclingTypewriter texts={PROMPTS} />
      </p>
    </div>
  )
}
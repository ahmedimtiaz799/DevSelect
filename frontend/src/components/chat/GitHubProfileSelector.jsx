import { useState } from 'react'
import { GitBranch } from 'lucide-react'

function getGithubUsername(url) {
  try {
    const parsed = new URL(url)
    const username = parsed.pathname.split('/').filter(Boolean)[0]
    return username ? `@${username}` : 'GitHub profile'
  } catch {
    const match = String(url).match(/github\.com\/([^/?#]+)/i)
    return match?.[1] ? `@${match[1]}` : 'GitHub profile'
  }
}

export function GitHubProfileSelector({ profiles, onSelect }) {
  const [selectedProfile, setSelectedProfile] = useState(profiles?.[0] ?? '')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!profiles || profiles.length === 0) return null

  const selected = profiles.includes(selectedProfile)
    ? selectedProfile
    : profiles[0]

  async function handleSubmit(e) {
    e.preventDefault()
    if (!selected || isSubmitting) return

    setIsSubmitting(true)
    await onSelect(selected)
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="w-full max-w-ai-msg rounded-2xl border border-gray-200 bg-white px-4 py-4 shadow-sm"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-dark/10 text-brand-dark">
          <GitBranch size={18} />
        </span>

        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold text-brand-dark">
            Multiple GitHub profiles found
          </h2>
          <p className="mt-1 text-sm leading-6 text-brand-muted">
            I found more than one GitHub profile in this CV. Select the profile you want DevSelect to evaluate.
          </p>
        </div>
      </div>

      <fieldset className="mt-4 space-y-2">
        {profiles.map((url) => {
          const isSelected = selected === url

          return (
            <label
              key={url}
              className={`flex min-h-[52px] cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors ${
                isSelected
                  ? 'border-brand-dark bg-brand-dark/5 ring-1 ring-brand-dark'
                  : 'border-gray-200 bg-white hover:border-brand-dark/40 hover:bg-gray-50'
              }`}
            >
              <input
                type="radio"
                name="github-profile"
                value={url}
                checked={isSelected}
                onChange={() => setSelectedProfile(url)}
                className="h-4 w-4 shrink-0 accent-brand-dark"
              />

              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-brand-dark">
                  {getGithubUsername(url)}
                </span>
                <span className="block truncate text-xs text-brand-muted">
                  {url}
                </span>
              </span>
            </label>
          )
        })}
      </fieldset>

      <div className="mt-4 flex justify-end">
        <button
          type="submit"
          disabled={!selected || isSubmitting}
          className="min-h-[44px] w-full rounded-lg bg-brand-dark px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-dark/90 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
        >
          {isSubmitting ? 'Continuing...' : 'Continue evaluation'}
        </button>
      </div>
    </form>
  )
}

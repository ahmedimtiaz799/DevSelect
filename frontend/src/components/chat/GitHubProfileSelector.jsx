import { useState } from 'react'
import { GitBranch } from 'lucide-react'

function getGitHubUsername(url) {
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
      className="w-full max-w-ai-msg rounded-2xl border border-ds-border bg-ds-surface px-4 py-4 shadow-sm"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-dsAlpha-accent/10 text-ds-text-strong">
          <GitBranch size={18} />
        </span>

        <div className="min-w-0 flex-1">
          <h2 className="text-base font-semibold text-ds-text-strong">
            Multiple GitHub profiles found
          </h2>
          <p className="mt-1 text-sm leading-6 text-ds-text-muted">
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
              className={`flex min-h-[52px] cursor-pointer items-center gap-3 rounded-xl border px-3 py-2.5 transition-colors focus-within:outline-none focus-within:ring-1 focus-within:ring-dsAlpha-focus-ring/70 ${
                isSelected
                  ? 'border-ds-accent bg-dsAlpha-accent/5 ring-1 ring-ds-accent'
                  : 'border-ds-border bg-ds-surface hover:border-dsAlpha-accent/40 hover:bg-gray-50'
              }`}
            >
              <input
                type="radio"
                name="github-profile"
                value={url}
                checked={isSelected}
                onChange={() => setSelectedProfile(url)}
                className="h-4 w-4 shrink-0 accent-ds-accent focus-visible:outline-none"
              />

              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-ds-text-strong">
                  {getGitHubUsername(url)}
                </span>
                <span className="block truncate text-xs text-ds-text-muted">
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
          className="min-h-[44px] w-full rounded-lg bg-ds-accent px-4 py-2 text-sm font-medium text-ds-text-inverse transition-colors hover:bg-dsAlpha-accent/90 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-dsAlpha-focus-ring/70 focus-visible:ring-offset-1 focus-visible:ring-offset-ds-bg sm:w-auto"
        >
          {isSubmitting ? 'Continuing...' : 'Continue evaluation'}
        </button>
      </div>
    </form>
  )
}

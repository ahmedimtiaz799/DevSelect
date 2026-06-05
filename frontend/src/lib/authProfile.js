function cleanDisplayValue(value) {
  if (typeof value !== 'string') return ''

  const trimmed = value.trim()
  if (!trimmed || /^https?:\/\//i.test(trimmed)) return ''

  return trimmed
}

function getProviders(user) {
  const providers = [
    user?.app_metadata?.provider,
    ...(Array.isArray(user?.app_metadata?.providers)
      ? user.app_metadata.providers
      : []),
    ...(Array.isArray(user?.identities)
      ? user.identities.map((identity) => identity?.provider)
      : []),
  ]

  return [...new Set(
    providers
      .filter((provider) => typeof provider === 'string')
      .map((provider) => provider.trim().toLowerCase())
      .filter(Boolean)
  )]
}

function getProviderLabel(providers) {
  const labels = {
    github: 'GitHub',
    google: 'Google',
    email: 'email',
  }
  const provider = providers.find((value) => labels[value])

  return provider ? `Signed in with ${labels[provider]}` : ''
}

function getIdentityData(user, provider) {
  if (!Array.isArray(user?.identities)) return {}

  const identity = user.identities.find(
    (item) =>
      typeof item?.provider === 'string' &&
      item.provider.trim().toLowerCase() === provider
  )

  return identity?.identity_data ?? {}
}

function getAvatarUrl(...values) {
  for (const value of values) {
    if (typeof value !== 'string') continue

    const trimmed = value.trim()
    if (/^https?:\/\//i.test(trimmed)) return trimmed
  }

  return null
}

export function getAuthProfileDisplay(user) {
  const metadata = user?.user_metadata ?? {}
  const providers = getProviders(user)
  const hasGoogleProvider = providers.includes('google')
  const googleIdentity = hasGoogleProvider ? getIdentityData(user, 'google') : {}
  const email =
    cleanDisplayValue(user?.email) ||
    cleanDisplayValue(metadata.email) ||
    cleanDisplayValue(googleIdentity.email)
  const username =
    cleanDisplayValue(metadata.user_name) ||
    cleanDisplayValue(metadata.preferred_username)
  const googleName =
    cleanDisplayValue(googleIdentity.full_name) ||
    cleanDisplayValue(googleIdentity.name)

  const displayName =
    cleanDisplayValue(metadata.full_name) ||
    cleanDisplayValue(metadata.name) ||
    googleName ||
    (hasGoogleProvider && email ? email.split('@')[0] : '') ||
    username ||
    (email ? email.split('@')[0] : '') ||
    'User'

  const avatarMatch = displayName.match(/[a-zA-Z0-9]/)

  return {
    displayName,
    subtitle: email || (username ? `@${username.replace(/^@/, '')}` : '') ||
      getProviderLabel(providers),
    avatarInitial: avatarMatch ? avatarMatch[0].toUpperCase() : 'U',
    avatarUrl: getAvatarUrl(
      metadata.avatar_url,
      metadata.picture,
      googleIdentity.avatar_url,
      googleIdentity.picture
    ),
    providerLabel: getProviderLabel(providers),
  }
}

let tempIdCounter = 0

export const CHAT_TITLE_MAX_LENGTH = 80
const UNKNOWN_ROLE_VALUES = new Set([
  'unknown role',
  'unknown',
  'n/a',
  'na',
  'none',
  'null',
  'undefined',
])

function cleanTitleValue(value) {
  return String(value ?? '')
    .replace(/[\r\n]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function normalizeCandidateRole(role) {
  const cleaned = cleanTitleValue(role)

  if (!cleaned || UNKNOWN_ROLE_VALUES.has(cleaned.toLowerCase())) {
    return null
  }

  return cleaned
}

export function normalizeChatTitle(title, fallback = 'New Chat') {
  const cleaned = cleanTitleValue(title)
  const fallbackTitle = cleanTitleValue(fallback) || 'New Chat'
  const value = cleaned || fallbackTitle

  if (value.length <= CHAT_TITLE_MAX_LENGTH) return value

  return `${value.slice(0, CHAT_TITLE_MAX_LENGTH - 3).trimEnd()}...`
}

export function truncateTitle(title, maxLength = 30) {
  const normalizedTitle = normalizeChatTitle(title)

  if (normalizedTitle.length > maxLength) {
    return `${normalizedTitle.slice(0, maxLength - 3).trimEnd()}...`
  }

  return normalizedTitle
}

export function parseCandidateTitle(title) {
  const cleanedTitle = cleanTitleValue(title)
  const normalizedTitle = cleanedTitle || 'Untitled Chat'
  const emDashSeparator = ' — '
  const hyphenSeparator = ' - '
  const separator = normalizedTitle.includes(emDashSeparator)
    ? emDashSeparator
    : normalizedTitle.includes(hyphenSeparator)
      ? hyphenSeparator
      : null

  if (!separator) {
    return {
      name: normalizedTitle,
      role: null,
      headerTitle: normalizedTitle,
      sidebarTitle: normalizedTitle,
    }
  }

  const separatorIndex = normalizedTitle.indexOf(separator)
  const parsedName = cleanTitleValue(normalizedTitle.slice(0, separatorIndex))
  const parsedRole = normalizeCandidateRole(
    normalizedTitle.slice(separatorIndex + separator.length)
  )
  const name = parsedName || normalizedTitle
  const headerTitle = parsedRole ? `${name} · ${parsedRole}` : name

  return {
    name,
    role: parsedRole,
    headerTitle,
    sidebarTitle: name,
  }
}

export function formatDate(isoString) {
  const date = new Date(isoString)
  const now = new Date()

  const isToday =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear()

  if (isToday) return 'Today'

  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)

  const isYesterday =
    date.getDate() === yesterday.getDate() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getFullYear() === yesterday.getFullYear()

  if (isYesterday) return 'Yesterday'

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function generateTempId() {
  tempIdCounter += 1
  return `temp_${Date.now()}_${tempIdCounter}`
}

export function extractGitHubUsername(url) {
  const cleaned = url
    .replace(/^https?:\/\/github\.com\//, '')
    .replace(/^github\.com\//, '');
  return cleaned.split('/')[0].toLowerCase();
}

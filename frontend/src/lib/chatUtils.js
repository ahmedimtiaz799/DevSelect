export function truncateTitle(title, maxLength = 30) {
  if (title.length > maxLength) return title.slice(0, maxLength) + '...'
  return title
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
  return 'temp_' + Date.now()
}

export function extractGitHubUsername(url) {
  const cleaned = url
    .replace(/^https?:\/\/github\.com\//, '')
    .replace(/^github\.com\//, '');
  return cleaned.split('/')[0].toLowerCase();
}
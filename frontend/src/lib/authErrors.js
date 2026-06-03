const GENERIC_AUTH_ERROR_MESSAGE = 'We could not sign you in. Please try again.'

function getErrorText(error) {
  if (typeof error === 'string') return error
  if (!error) return ''

  return [
    error.message,
    error.error,
    error.error_description,
    error.description,
    error.code,
    error.name,
    error.status,
  ]
    .filter(Boolean)
    .join(' ')
}

export function getAuthErrorMessage(error) {
  const text = getErrorText(error).toLowerCase()

  if (!text) return GENERIC_AUTH_ERROR_MESSAGE

  if (
    text.includes('cancel') ||
    text.includes('closed') ||
    text.includes('denied') ||
    text.includes('access_denied') ||
    text.includes('popup')
  ) {
    return 'Sign-in was cancelled. Please try again.'
  }

  if (
    text.includes('network') ||
    text.includes('fetch') ||
    text.includes('connection') ||
    text.includes('offline') ||
    text.includes('timeout') ||
    text.includes('timed out') ||
    text.includes('internet')
  ) {
    return 'Could not connect. Please check your internet connection and try again.'
  }

  if (
    text.includes('session expired') ||
    text.includes('expired session') ||
    text.includes('invalid session') ||
    text.includes('token expired') ||
    text.includes('refresh token') ||
    text.includes('invalid_grant')
  ) {
    return 'Your session expired. Please sign in again.'
  }

  if (
    text.includes('oauth') ||
    text.includes('provider') ||
    text.includes('unavailable') ||
    text.includes('service') ||
    text.includes('server') ||
    text.includes('502') ||
    text.includes('503')
  ) {
    return 'Sign-in is temporarily unavailable. Please try again later.'
  }

  return GENERIC_AUTH_ERROR_MESSAGE
}

export const MAX_USER_INPUT_CHARS = 2000
export const MAX_USER_INPUT_WARNING_CHARS = 1800
export const USER_INPUT_TOO_LONG_MESSAGE = 'Message is too long. Please keep it under 2000 characters.'

export function capUserInput(value) {
  return String(value ?? '').slice(0, MAX_USER_INPUT_CHARS)
}

export function normalizeUserInput(value) {
  return capUserInput(value).trim()
}

const DEFAULT_ERROR_MESSAGE = 'The request could not be completed. Please try again.';
const SAFE_ERROR_CODE = /^[A-Z][A-Z0-9_]{0,63}$/;

const UNSAFE_ERROR_PATTERNS = [
  /traceback|stack\s*trace|exception/i,
  /\b(?:select|insert\s+into|update\s+\S+\s+set|delete\s+from|drop\s+table|create\s+table|alter\s+table|truncate\s+table|union\s+select|sqlstate)\b/i,
  /syntax error at|relation .* does not exist|postgres|psycopg|sqlalchemy/i,
  /\b(?:authorization|bearer|access_token|refresh_token|service_role)\b/i,
  /\b(?:api[_ ]?key|secret|password|database_url|redis[_ ]?token)\b/i,
  /\b(?:raw_cv_text|pdf_preview_text|resume_payload|thread_id)\b/i,
  /\b(?:system prompt|user prompt|prompt\s*[:=]|provider payload|provider response|provider output)\b/i,
  /\b(?:cv text|resume text)\b/i,
  /(?:https?|postgres(?:ql)?|redis):\/\//i,
  /\b[A-Za-z]:[\\/]/,
  /\/(?:home|app|tmp|var|usr|etc|opt|workspace|Users)\//,
  /\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/,
  /\b(?:sk-|AIza|gsk_)[A-Za-z0-9_-]{8,}\b/,
];

export function safeUserErrorMessage(message, fallback = DEFAULT_ERROR_MESSAGE) {
  if (typeof message !== 'string') return fallback;

  const value = message.trim();
  if (
    !value ||
    value.length > 240 ||
    value.includes('\n') ||
    value.includes('\r') ||
    UNSAFE_ERROR_PATTERNS.some((pattern) => pattern.test(value))
  ) {
    return fallback;
  }

  return value;
}

export function safeErrorPayload(payload, fallback = DEFAULT_ERROR_MESSAGE) {
  const code =
    typeof payload?.code === 'string' && SAFE_ERROR_CODE.test(payload.code)
      ? payload.code
      : undefined;
  const retryAfter = Number(payload?.retry_after_seconds);

  return {
    error: safeUserErrorMessage(payload?.error, fallback),
    ...(code ? { code } : {}),
    ...(Number.isFinite(retryAfter) && retryAfter > 0
      ? { retry_after_seconds: Math.ceil(retryAfter) }
      : {}),
  };
}

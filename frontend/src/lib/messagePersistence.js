const CV_UPLOAD_PREFIX = '__DEVSELECT_CV_UPLOAD__'
const ASSISTANT_MESSAGE_PREFIX = '__DEVSELECT_ASSISTANT_MESSAGE__'
const REPORT_CONTEXT_HINTS = [
  'Candidate Overview',
  'Hiring Recommendation',
  'Skill Match Assessment',
  'Detected Role',
]

export const EVALUATION_REPORT_MESSAGE_TYPE = 'evaluation_report'
export const FOLLOW_UP_ANSWER_MESSAGE_TYPE = 'follow_up_answer'

export function serializeUploadMessage(message) {
  return `${CV_UPLOAD_PREFIX}${JSON.stringify({
    content: message.content ?? '',
    fileName: message.fileName ?? '',
    fileType: message.fileType ?? '',
  })}`
}

export function serializeAssistantMessage(message, messageType) {
  return `${ASSISTANT_MESSAGE_PREFIX}${JSON.stringify({
    content: message.content ?? '',
    message_type: messageType,
  })}`
}

export function isEvaluationReportMessage(message) {
  if (message?.role !== 'assistant') return false

  const messageType = message.message_type || message.kind || ''
  if (messageType === EVALUATION_REPORT_MESSAGE_TYPE) return true
  if (messageType) return false

  const content = typeof message.content === 'string'
    ? message.content
    : ''

  return REPORT_CONTEXT_HINTS.some((hint) => content.includes(hint))
}

export function normalizePersistedMessage(message) {
  if (
    typeof message.content !== 'string'
  ) {
    return message
  }

  if (
    message.role !== 'user' ||
    typeof message.content !== 'string' ||
    !message.content.startsWith(CV_UPLOAD_PREFIX)
  ) {
    if (
      message.role !== 'assistant' ||
      !message.content.startsWith(ASSISTANT_MESSAGE_PREFIX)
    ) {
      return message
    }

    try {
      const payload = JSON.parse(message.content.slice(ASSISTANT_MESSAGE_PREFIX.length))
      const messageType = typeof payload.message_type === 'string'
        ? payload.message_type
        : typeof payload.kind === 'string'
          ? payload.kind
          : ''

      return {
        ...message,
        content: typeof payload.content === 'string' ? payload.content : '',
        ...(messageType ? { message_type: messageType } : {}),
      }
    } catch {
      return message
    }
  }

  try {
    const payload = JSON.parse(message.content.slice(CV_UPLOAD_PREFIX.length))
    return {
      ...message,
      content: typeof payload.content === 'string' ? payload.content : '',
      fileName: typeof payload.fileName === 'string' ? payload.fileName : '',
      fileType: typeof payload.fileType === 'string' ? payload.fileType : '',
    }
  } catch {
    return message
  }
}

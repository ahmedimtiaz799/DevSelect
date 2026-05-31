const CV_UPLOAD_PREFIX = '__DEVSELECT_CV_UPLOAD__'

export function serializeUploadMessage(message) {
  return `${CV_UPLOAD_PREFIX}${JSON.stringify({
    content: message.content ?? '',
    fileName: message.fileName ?? '',
    fileType: message.fileType ?? '',
  })}`
}

export function normalizePersistedMessage(message) {
  if (
    message.role !== 'user' ||
    typeof message.content !== 'string' ||
    !message.content.startsWith(CV_UPLOAD_PREFIX)
  ) {
    return message
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

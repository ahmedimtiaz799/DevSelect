import { supabase } from './supabase'
import { normalizeUserInput } from './textLimits'

const BASE_URL = import.meta.env.VITE_API_URL
const UPLOAD_CONNECTION_FAILED_MESSAGE =
  'Upload connection failed before report streaming started. Please check your connection and try once later.'
const UPLOAD_RESPONSE_INVALID_MESSAGE =
  'Upload response could not be read. Please try again later.'

function getBrowserTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || ''
  } catch {
    return ''
  }
}

async function getAuthHeaders() {
  const { data } = await supabase.auth.getSession()
  return {
    'Authorization': `Bearer ${data.session.access_token}`,
    'Content-Type': 'application/json',
  }
}

export async function apiPost(path, body) {
  const headers = await getAuthHeaders()
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  return response.json()
}

export async function apiGet(path) {
  const headers = await getAuthHeaders()
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'GET',
    headers,
  })
  return response.json()
}

export async function uploadCV(chatId, file, threadId, recruiterInstruction) {
  const { data } = await supabase.auth.getSession()
  const formData = new FormData()
  const instruction = normalizeUserInput(recruiterInstruction)
  const evaluationTimezone = getBrowserTimezone()
  formData.append('file', file)
  if (threadId) formData.append('thread_id', threadId)
  if (instruction) formData.append('recruiter_instruction', instruction)
  if (evaluationTimezone) formData.append('evaluation_timezone', evaluationTimezone)

  let response
  try {
    response = await fetch(`${BASE_URL}/api/chat/${chatId}/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${data.session.access_token}`,
      },
      body: formData,
    })
  } catch {
    throw new Error(UPLOAD_CONNECTION_FAILED_MESSAGE)
  }

  let result
  try {
    result = await response.json()
  } catch {
    result = {
      error: UPLOAD_RESPONSE_INVALID_MESSAGE,
      code: 'UPLOAD_RESPONSE_INVALID',
    }
  }
  return { status: response.status, data: result }
}

export async function resumePipeline(chatId, threadId, selectedProfile) {
  return apiPost(`/api/chat/${chatId}/resume`, {
    thread_id: threadId,
    selected_profile: selectedProfile ?? null,
  })
}

export async function followUpQuestion(chatId, question) {
  const headers = await getAuthHeaders()
  const response = await fetch(`${BASE_URL}/api/chat/${chatId}/follow-up`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ question: normalizeUserInput(question) }),
  })

  const result = await response.json()
  return { status: response.status, data: result }
}

export async function deleteChatWithCleanup(chatId) {
  const headers = await getAuthHeaders()
  const response = await fetch(`${BASE_URL}/api/chat/${chatId}/delete`, {
    method: 'POST',
    headers,
  })
  return response.ok
}

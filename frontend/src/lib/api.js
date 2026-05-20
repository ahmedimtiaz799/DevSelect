import { supabase } from './supabase'

const BASE_URL = import.meta.env.VITE_API_URL

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

export async function uploadCV(chatId, file, threadId) {
  const { data } = await supabase.auth.getSession()
  const formData = new FormData()
  formData.append('file', file)
  if (threadId) formData.append('thread_id', threadId)

  const response = await fetch(`${BASE_URL}/api/chat/${chatId}/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${data.session.access_token}`,
    },
    body: formData,
  })

  const result = await response.json()
  return { status: response.status, data: result }
}

export async function resumePipeline(chatId, threadId, selectedProfile) {
  return apiPost(`/api/chat/${chatId}/resume`, {
    thread_id: threadId,
    selected_profile: selectedProfile ?? null,
  })
}
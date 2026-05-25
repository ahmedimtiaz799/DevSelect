import { fetchEventSource } from '@microsoft/fetch-event-source';

const BASE_URL = import.meta.env.VITE_API_URL;

export async function streamChatResponse(
  chatId,
  threadId,
  resumePayload,
  token,
  handlers
) {
  const { onMeta, onStatus, onToken, onDone, onError } = handlers;

  const controller = new AbortController();

  const url =
    `${BASE_URL}/api/chat/${chatId}/stream` +
    `?thread_id=${encodeURIComponent(threadId)}` +
    `&resume_payload=${encodeURIComponent(JSON.stringify(resumePayload))}`;

  fetchEventSource(url, {
    method: 'GET',
    signal: controller.signal,
    headers: {
      Authorization: `Bearer ${token}`,
    },
    onmessage(event) {
      if (event.event === 'meta') {
        onMeta(JSON.parse(event.data));
        return;
      }
      if (event.event === 'status') {
        onStatus(JSON.parse(event.data).text);
        return;
      }
      if (event.event === 'token') {
        onToken(JSON.parse(event.data).text);
        return;
      }
      if (event.event === 'done') {
        onDone();
        controller.abort();
        return;
      }
      if (event.event === 'error') {
        onError(JSON.parse(event.data).error);
        controller.abort();
        return;
      }
      console.warn('Unknown SSE event type:', event.event);
    },
    onerror(err) {
      onError(err?.message ?? 'Stream connection failed');
      throw err;
    },
  });

  return () => controller.abort();
}
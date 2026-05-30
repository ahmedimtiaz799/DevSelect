import { fetchEventSource } from '@microsoft/fetch-event-source';

const BASE_URL = import.meta.env.VITE_API_URL;

function isAbortError(err) {
  return (
    err?.name === 'AbortError' ||
    err?.message?.toLowerCase().includes('aborted')
  );
}

function parseEventData(data) {
  try {
    return JSON.parse(data);
  } catch {
    return {};
  }
}

export function streamChatResponse(
  chatId,
  threadId,
  resumePayload,
  token,
  handlers
) {
  const { onMeta, onStatus, onToken, onDone, onError } = handlers;

  const controller = new AbortController();
  let intentionalAbort = false;
  let settled = false;

  function abortStream() {
    intentionalAbort = true;
    controller.abort();
  }

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
        settled = true;
        onDone();
        abortStream();
        return;
      }
      if (event.event === 'error') {
        settled = true;
        onError(parseEventData(event.data));
        abortStream();
        return;
      }
      console.warn('Unknown SSE event type:', event.event);
    },
    onerror(err) {
      if (intentionalAbort || controller.signal.aborted || isAbortError(err)) {
        return;
      }
      throw err;
    },
    onclose() {
      if (settled || intentionalAbort || controller.signal.aborted) {
        return;
      }
      settled = true;
      onError({
        error: 'Evaluation stopped unexpectedly. Please try again.',
        code: 'UNEXPECTED_STREAM_END',
      });
    },
  }).catch((err) => {
    if (intentionalAbort || controller.signal.aborted || isAbortError(err)) {
      return;
    }
    settled = true;
    onError({ error: err?.message ?? 'Stream connection failed' });
  });

  return abortStream;
}

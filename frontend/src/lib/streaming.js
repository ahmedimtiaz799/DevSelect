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

function retryAfterSeconds(response, payload) {
  const retryAfter = Number(
    payload?.retry_after_seconds ?? response.headers.get('Retry-After')
  );

  return Number.isFinite(retryAfter) && retryAfter > 0
    ? Math.ceil(retryAfter)
    : null;
}

function safeBackendErrorMessage(message) {
  if (typeof message !== 'string') return '';

  const value = message.trim();
  if (!value || value.length > 240) return '';

  const lower = value.toLowerCase();
  if (
    lower.includes('traceback') ||
    lower.includes('stack trace') ||
    lower.includes('exception') ||
    lower.includes('api key') ||
    lower.includes('secret') ||
    lower.includes('token=')
  ) {
    return '';
  }

  return value;
}

function streamStartupCode(status) {
  if (status === 429) return 'STREAM_RATE_LIMITED';
  if (status === 503) return 'STREAM_SERVICE_UNAVAILABLE';
  return 'STREAM_START_FAILED';
}

function streamStartupFallbackMessage(status, retryAfter) {
  if (status === 429 && retryAfter) {
    return `Too many requests. Please try again in ${retryAfter} seconds.`;
  }
  if (status === 429) {
    return 'Too many requests. Please wait a moment and try again.';
  }
  if (status === 503) {
    return 'AI evaluation is temporarily unavailable. Please try again later.';
  }
  return 'Streaming could not start. Please try again.';
}

async function readStreamStartupPayload(response) {
  try {
    return await response.clone().json();
  } catch {
    return {};
  }
}

async function parseStreamStartupError(response) {
  const payload = await readStreamStartupPayload(response);
  const retryAfter = retryAfterSeconds(response, payload);
  const safeError = safeBackendErrorMessage(payload?.error);
  const error =
    response.status === 429 && retryAfter
      ? streamStartupFallbackMessage(response.status, retryAfter)
      : safeError || streamStartupFallbackMessage(response.status, retryAfter);

  return {
    error,
    code: payload?.code || streamStartupCode(response.status),
    retry_after_seconds: retryAfter,
    status: response.status,
  };
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
    openWhenHidden: true,
    headers: {
      Authorization: `Bearer ${token}`,
    },
    async onopen(response) {
      if (response.ok) return;

      settled = true;
      onError(await parseStreamStartupError(response));
      abortStream();
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

export function streamFollowUpResponse(chatId, question, token, handlers) {
  const { onToken, onDone, onError } = handlers;

  const controller = new AbortController();
  let intentionalAbort = false;
  let settled = false;

  function abortStream() {
    intentionalAbort = true;
    controller.abort();
  }

  fetchEventSource(`${BASE_URL}/api/chat/${chatId}/follow-up/stream`, {
    method: 'POST',
    signal: controller.signal,
    openWhenHidden: true,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ question }),
    async onopen(response) {
      if (response.ok) return;

      settled = true;
      onError(await parseStreamStartupError(response));
      abortStream();
    },
    onmessage(event) {
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
      console.warn('Unknown follow-up SSE event type:', event.event);
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
        error: 'Follow-up answer failed. Please try again.',
        code: 'UNEXPECTED_STREAM_END',
      });
    },
  }).catch((err) => {
    if (intentionalAbort || controller.signal.aborted || isAbortError(err)) {
      return;
    }
    settled = true;
    onError({ error: err?.message ?? 'Follow-up answer failed. Please try again.' });
  });

  return abortStream;
}

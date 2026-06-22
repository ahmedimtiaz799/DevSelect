import assert from 'node:assert/strict';
import test from 'node:test';

import {
  safeErrorPayload,
  safeUserErrorMessage,
} from '../src/lib/errorSafety.js';

const fallback = 'Safe fallback message.';
const sentinels = [
  'raw_cv_text=CANDIDATE_PRIVATE_CV_TEXT',
  'system prompt: INTERNAL_RECRUITER_PROMPT',
  'prompt=PRIVATE_MODEL_INSTRUCTION',
  "SELECT * FROM auth.users WHERE password = 'private'",
  'DROP TABLE public.messages',
  'Bearer eyJFAKEHEADER.FAKEPAYLOAD.FAKESIGNATURE',
  'https://private.example.test/provider?token=private',
  'Traceback (most recent call last): RuntimeError',
  String.raw`C:\private\resume\candidate.pdf`,
  'provider output=PRIVATE_MODEL_RESPONSE',
  'thread_id=private-evaluation-thread',
  '/tmp/private-candidate.pdf',
];

test('unsafe frontend error strings always use the safe fallback', () => {
  for (const sentinel of sentinels) {
    assert.equal(safeUserErrorMessage(sentinel, fallback), fallback);
  }
});

test('safe frontend error strings remain usable', () => {
  const message = 'Evaluation failed. Please try again.';
  assert.equal(safeUserErrorMessage(message, fallback), message);
});

test('unsafe SSE payloads are sanitized before display', () => {
  for (const sentinel of sentinels) {
    const payload = safeErrorPayload(
      {
        error: sentinel,
        code: 'SAFE_CODE',
        retry_after_seconds: 12,
      },
      fallback
    );
    assert.equal(payload.error, fallback);
    assert.equal(payload.code, 'SAFE_CODE');
    assert.equal(payload.retry_after_seconds, 12);
    assert.equal(JSON.stringify(payload).includes(sentinel), false);
  }
});

test('unsafe or identifier-like error codes are discarded', () => {
  const payload = safeErrorPayload(
    {
      error: 'Evaluation failed. Please try again.',
      code: 'thread_id=private-evaluation-thread',
    },
    fallback
  );
  assert.equal('code' in payload, false);
});

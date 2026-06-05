import { useState, useEffect, useRef } from 'react';
import { useChatStore } from '../store/chatStore';
import { useChatHistory } from './useChatHistory';
import { streamChatResponse } from '../lib/streaming';
import { followUpQuestion, uploadCV, resumePipeline } from '../lib/api';
import { generateTempId, extractGitHubUsername, normalizeChatTitle } from '../lib/chatUtils';
import {
  EVALUATION_REPORT_MESSAGE_TYPE,
  FINAL_ERROR_MESSAGE_TYPE,
  FOLLOW_UP_ANSWER_MESSAGE_TYPE,
  isEvaluationReportMessage,
  serializeAssistantMessage,
  serializeUploadMessage,
} from '../lib/messagePersistence';
import { supabase } from '../lib/supabase';
import { normalizeUserInput } from '../lib/textLimits';

const PLACEHOLDER_ROLE_LABELS = new Set([
  'unknown role',
  'unknown title',
  'not detected',
  'not found',
  'n/a',
  'na',
  'none',
  'null',
]);
const PRE_CV_GUIDANCE_MESSAGE = 'Please upload a candidate CV to begin an evaluation.';
const MESSAGE_SAVE_FAILED_MESSAGE = 'Message could not be saved. Please check your connection and try again.';
const GENERATING_STATUS_MIN_DISPLAY_MS = 400;
const BUDGET_LIMIT_MESSAGES = {
  DAILY_EVALUATION_LIMIT_REACHED: 'Daily evaluation limit reached. Please try again tomorrow.',
  DAILY_USER_TOKEN_LIMIT_REACHED: 'Daily AI usage limit reached. Please try again tomorrow.',
  DAILY_GLOBAL_TOKEN_LIMIT_REACHED: 'Daily AI budget limit reached. Please try again tomorrow.',
  DAILY_AI_BUDGET_LIMIT_REACHED: 'Daily AI budget limit reached. Please try again tomorrow.',
};
function cleanMetaText(value) {
  return typeof value === 'string' ? value.trim() : '';
}

function getValidRole(role) {
  const value = cleanMetaText(role);
  return value && !PLACEHOLDER_ROLE_LABELS.has(value.toLowerCase())
    ? value
    : '';
}

function getCurrentTitleRole(title) {
  const parts = cleanMetaText(title).split(' — ');
  return parts.length > 1 ? getValidRole(parts.slice(1).join(' — ')) : '';
}

function isGeneratingRecommendationStatus(text) {
  return cleanMetaText(text).toLowerCase().startsWith('generating recommendation');
}

export function useChat(chatId) {
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessagesByChat, setStatusMessagesByChat] = useState({});

  const cleanupRef = useRef(null);
  const activeRunRef = useRef(null);
  const runIdRef = useRef(0);
  const saveWarningChatsRef = useRef(new Set());

  const threadIds = useChatStore((s) => s.threadIds);
  const addMessage = useChatStore((s) => s.addMessage);
  const setThreadId = useChatStore((s) => s.setThreadId);
  const setPendingProfiles = useChatStore((s) => s.setPendingProfiles);
  const clearPendingProfiles = useChatStore((s) => s.clearPendingProfiles);
  const updateChatTitle = useChatStore((s) => s.updateChatTitle);

  const { renameChat, touchChatActivity } = useChatHistory();

  useEffect(() => {
    return () => {
      if (cleanupRef.current) {
        cleanupRef.current();
      }
    };
  }, []);

  const hasThread = (targetId) => !!threadIds[targetId]

  function getUserMessagePayload(file, userText) {
    const text = normalizeUserInput(userText);

    if (!file) {
      return { content: text };
    }

    return {
      content: text,
      fileName: file.name,
      fileType: file.type,
    };
  }

  async function persistUserUploadMessage(targetId, messagePayload) {
    const { error } = await supabase.from('messages').insert({
      chat_id: targetId,
      role: 'user',
      content: serializeUploadMessage(messagePayload),
    });

    if (error) {
      console.warn('Failed to persist user upload message:', error.message);
      addMessageSaveWarning(targetId);
    }
  }

  async function persistPlainMessages(targetId, messages) {
    const { error } = await supabase.from('messages').insert(
      messages.map((message) => ({
        chat_id: targetId,
        role: message.role,
        content: message.role === 'assistant' && message.message_type
          ? serializeAssistantMessage(message, message.message_type)
          : message.content,
      }))
    );

    if (error) {
      console.warn('Failed to persist chat guidance messages:', error.message);
      addMessageSaveWarning(targetId);
    }
  }

  async function addAndPersistFinalError(targetId, content, run, errorPayload = {}) {
    if (!targetId || !content || run?.finalErrorHandled) return;

    if (run) {
      run.finalErrorHandled = true;
    }

    const retryAfter = Number(errorPayload?.retry_after_seconds);
    const assistantMessage = {
      id: generateTempId(),
      role: 'assistant',
      content,
      message_type: FINAL_ERROR_MESSAGE_TYPE,
      ...(typeof errorPayload?.code === 'string'
        ? { error_code: errorPayload.code }
        : {}),
      ...(Number.isFinite(retryAfter) && retryAfter > 0
        ? { retry_after_seconds: retryAfter }
        : {}),
      chat_id: targetId,
    };

    addMessage(targetId, assistantMessage);
    await persistPlainMessages(targetId, [assistantMessage]);
  }

  function addMessageSaveWarning(targetId) {
    if (!targetId || saveWarningChatsRef.current.has(targetId)) return;

    saveWarningChatsRef.current.add(targetId);
    addMessage(targetId, {
      id: generateTempId(),
      role: 'system',
      content: MESSAGE_SAVE_FAILED_MESSAGE,
      chat_id: targetId,
    });
  }

  function hasCompletedReport(targetId) {
    const chatMessages = useChatStore.getState().messages[targetId] ?? [];

    return chatMessages.some(isEvaluationReportMessage);
  }

  async function sendPreCvGuidanceMessage(userText, targetId) {
    const text = normalizeUserInput(userText);
    if (!text || !targetId) return;

    const userMessage = {
      id: generateTempId(),
      role: 'user',
      content: text,
      chat_id: targetId,
    };
    const assistantMessage = {
      id: generateTempId(),
      role: 'assistant',
      content: PRE_CV_GUIDANCE_MESSAGE,
      chat_id: targetId,
    };

    addMessage(targetId, userMessage);
    addMessage(targetId, assistantMessage);
    await touchChatActivity(targetId);
    await persistPlainMessages(targetId, [userMessage, assistantMessage]);
  }

  function addStatusMessage(chatId, text) {
    setStatusMessagesByChat((current) => ({
      ...current,
      [chatId]: (current[chatId] ?? []).includes(text)
        ? (current[chatId] ?? [])
        : [...(current[chatId] ?? []), text],
    }));
  }

  function clearStatusMessages(chatId) {
    setStatusMessagesByChat((current) => {
      if (!current[chatId]) return current;

      const next = { ...current };
      delete next[chatId];
      return next;
    });
  }

  function getSafeBackendMessage(message) {
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

  function getStreamErrorMessage(errorPayload) {
    if (errorPayload?.code === 'GEMINI_QUOTA_EXCEEDED') {
      const retryAfter = Number(errorPayload.retry_after_seconds);

      if (retryAfter > 0) {
        return `Gemini quota reached. Please wait about ${retryAfter} seconds and try again.`;
      }

      return 'Gemini quota reached. Please wait and try again.';
    }

    if (
      errorPayload?.code === 'EVALUATION_STOPPED_UNEXPECTEDLY' ||
      errorPayload?.code === 'UNEXPECTED_STREAM_END'
    ) {
      return 'Evaluation stopped unexpectedly. Please try again.';
    }

    if (errorPayload?.code === 'STREAM_RATE_LIMITED') {
      const retryAfter = Number(errorPayload.retry_after_seconds);

      if (retryAfter > 0) {
        return `Too many requests. Please try again in ${retryAfter} seconds.`;
      }

      return errorPayload?.error || 'Too many requests. Please wait a moment and try again.';
    }

    if (errorPayload?.code === 'STREAM_SERVICE_UNAVAILABLE') {
      return errorPayload?.error || 'AI evaluation is temporarily unavailable. Please try again later.';
    }

    if (errorPayload?.code === 'STREAM_START_FAILED') {
      return errorPayload?.error || 'Streaming could not start. Please try again.';
    }

    const safeError = getSafeBackendMessage(errorPayload?.error);
    if (safeError) return safeError;

    return 'Evaluation failed. Please try again.';
  }

  function getRequestErrorMessage(error) {
    return error?.message || 'Evaluation failed. Please try again.';
  }

  function getBudgetLimitMessage(response) {
    const code = response?.data?.code;

    if (BUDGET_LIMIT_MESSAGES[code]) {
      return BUDGET_LIMIT_MESSAGES[code];
    }

    if (
      response?.status === 429 &&
      typeof code === 'string' &&
      code.startsWith('DAILY_')
    ) {
      return BUDGET_LIMIT_MESSAGES.DAILY_AI_BUDGET_LIMIT_REACHED;
    }

    if (
      response?.status === 429 &&
      typeof response?.data?.error === 'string' &&
      response.data.error.toLowerCase().includes('daily')
    ) {
      return BUDGET_LIMIT_MESSAGES.DAILY_AI_BUDGET_LIMIT_REACHED;
    }

    return '';
  }

  function ensureReadyToStream(result) {
    if (!result?.thread_id || !result?.resume_payload?.scenario) {
      throw new Error(result?.error || 'Evaluation could not be started. Please try again.');
    }
  }

  function startRun(targetId) {
    const run = {
      id: runIdRef.current + 1,
      chatId: targetId,
      stopped: false,
      assistantTempId: null,
      hasReceivedToken: false,
      generatingStatusAt: null,
      tokenHandoffUntil: null,
      tokenHandoffTimer: null,
      tokenBuffer: '',
      tokensRevealed: false,
      finalErrorHandled: false,
    };

    runIdRef.current = run.id;
    activeRunRef.current = run;
    return run;
  }

  function isRunActive(run) {
    return !!run && activeRunRef.current?.id === run.id && !run.stopped;
  }

  function clearTokenHandoffTimer(run) {
    if (!run?.tokenHandoffTimer) return;

    clearTimeout(run.tokenHandoffTimer);
    run.tokenHandoffTimer = null;
  }

  function finishRun(run) {
    clearTokenHandoffTimer(run);

    if (activeRunRef.current?.id === run?.id) {
      activeRunRef.current = null;
    }
  }

  function appendAssistantContent(targetId, assistantTempId, content, run) {
    if (!content || !isRunActive(run)) return;

    useChatStore.setState((state) => {
      if (!isRunActive(run)) return;

      const chatMessages = state.messages[targetId];
      if (!chatMessages || chatMessages.length === 0) return;

      const assistantIndex = chatMessages.findIndex(
        (message) => message.id === assistantTempId
      );
      if (assistantIndex === -1) return;

      const assistantMessage = chatMessages[assistantIndex];
      if (assistantMessage.role !== 'assistant') return;

      const updatedMessages = [...chatMessages];
      updatedMessages[assistantIndex] = {
        ...assistantMessage,
        content: assistantMessage.content + content,
      };

      return {
        messages: {
          ...state.messages,
          [targetId]: updatedMessages,
        },
      };
    });
  }

  function revealBufferedTokens(targetId, assistantTempId, run) {
    if (!isRunActive(run) || run.tokensRevealed) return;

    clearTokenHandoffTimer(run);
    run.tokensRevealed = true;
    clearStatusMessages(targetId);

    const bufferedContent = run.tokenBuffer;
    run.tokenBuffer = '';
    appendAssistantContent(targetId, assistantTempId, bufferedContent, run);
  }

  async function waitForTokenHandoff(targetId, assistantTempId, run) {
    if (run.tokensRevealed || !run.hasReceivedToken) return;

    const remaining = Math.max(0, (run.tokenHandoffUntil ?? 0) - Date.now());
    if (remaining > 0) {
      await new Promise((resolve) => setTimeout(resolve, remaining));
    }

    revealBufferedTokens(targetId, assistantTempId, run);
  }

  function removeAssistantMessage(targetId, assistantTempId) {
    if (!assistantTempId) return;

    useChatStore.setState((state) => {
      const chatMessages = state.messages[targetId] ?? [];

      return {
        messages: {
          ...state.messages,
          [targetId]: chatMessages.filter((m) => m.id !== assistantTempId),
        },
      };
    });
  }

  function addStoppedMessage(targetId) {
    if (!targetId) return;

    addMessage(targetId, {
      id: generateTempId(),
      role: 'system',
      content: 'Response stopped.',
      chat_id: targetId,
    });
  }

  function stopProcessing() {
    const run = activeRunRef.current;
    const targetId = run?.chatId ?? chatId;

    if (run) {
      run.stopped = true;
      clearTokenHandoffTimer(run);
      run.tokenBuffer = '';
    }

    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }

    setIsLoading(false);
    setIsStreaming(false);

    if (targetId) {
      clearStatusMessages(targetId);
      setThreadId(targetId, null);
    }

    if (run?.assistantTempId) {
      removeAssistantMessage(run.chatId, run.assistantTempId);
    }

    if (run || isLoading || isStreaming) {
      addStoppedMessage(targetId);
    }

    activeRunRef.current = null;
  }

  async function sendMessage(file, userText, overrideChatId) {
    const targetId = overrideChatId ?? chatId;

    if (!file) {
      if (hasCompletedReport(targetId)) {
        const run = startRun(targetId);
        await sendFollowUpMessage(userText, targetId, run);
        return;
      }

      await sendPreCvGuidanceMessage(userText, targetId);
      return;
    }

    const run = startRun(targetId);
    setIsLoading(true);
    clearStatusMessages(targetId);

    const tempId = generateTempId();
    const userMessagePayload = getUserMessagePayload(file, userText);
    addMessage(targetId, {
      id: tempId,
      role: 'user',
      ...userMessagePayload,
      chat_id: targetId,
    });

    try {
      await persistUserUploadMessage(targetId, userMessagePayload);
      await touchChatActivity(targetId);
      if (!isRunActive(run)) return;

      const response = await uploadCV(
        targetId,
        file,
        threadIds[targetId],
        userMessagePayload.content
      );

      if (!isRunActive(run)) return;

      const budgetLimitMessage = getBudgetLimitMessage(response);
      if (budgetLimitMessage) {
        const assistantMessage = {
          id: generateTempId(),
          role: 'assistant',
          content: budgetLimitMessage,
          chat_id: targetId,
        };

        setIsLoading(false);
        clearStatusMessages(targetId);
        finishRun(run);
        addMessage(targetId, assistantMessage);
        await persistPlainMessages(targetId, [assistantMessage]);
        return;
      }

      if (response.status !== 200 && response.status !== 202) {
        throw new Error(response.data?.error || 'Evaluation failed. Please try again.');
      }

      if (response.status === 202) {
        const profiles = response.data.profiles;
        const uniqueUsernames = [
          ...new Set(profiles.map(extractGitHubUsername)),
        ];

        setThreadId(targetId, response.data.thread_id);

        if (uniqueUsernames.length === 1) {
          const resolvedUrl = `https://github.com/${uniqueUsernames[0]}`;
          const result = await resumePipeline(
            targetId,
            response.data.thread_id,
            resolvedUrl
          );
          if (!isRunActive(run)) return;

          ensureReadyToStream(result);
          await startSSEStream(
            result.thread_id,
            result.resume_payload,
            targetId,
            run
          );
          return;
        }

        const cleanProfiles = uniqueUsernames.map(
          (username) => `https://github.com/${username}`
        );
        setIsLoading(false);
        finishRun(run);
        setPendingProfiles(targetId, cleanProfiles);
        return;
      }

      if (response.status === 200) {
        setThreadId(targetId, response.data.thread_id);
        ensureReadyToStream(response.data);
        await startSSEStream(
          response.data.thread_id,
          response.data.resume_payload,
          targetId,
          run
        );
        return;
      }

      setIsLoading(false);
      finishRun(run);
    } catch (error) {
      if (!isRunActive(run)) return;

      setIsLoading(false);
      clearStatusMessages(targetId);
      finishRun(run);
      await addAndPersistFinalError(
        targetId,
        getRequestErrorMessage(error),
        run
      );
    }
  }

  async function sendFollowUpMessage(userText, targetId, run) {
    const text = normalizeUserInput(userText);
    if (!text || !targetId) {
      finishRun(run);
      return;
    }

    setIsLoading(true);
    clearStatusMessages(targetId);

    const userMessage = {
      id: generateTempId(),
      role: 'user',
      content: text,
      chat_id: targetId,
    };
    addMessage(targetId, userMessage);

    try {
      await touchChatActivity(targetId);
      const response = await followUpQuestion(targetId, text);
      if (!isRunActive(run)) return;

      if (response.status !== 200 || !response.data?.answer) {
        throw new Error(response.data?.error || 'Follow-up answer failed. Please try again.');
      }

      const assistantMessage = {
        id: generateTempId(),
        role: 'assistant',
        content: response.data.answer,
        message_type: FOLLOW_UP_ANSWER_MESSAGE_TYPE,
        chat_id: targetId,
      };
      addMessage(targetId, assistantMessage);
      await persistPlainMessages(targetId, [userMessage, assistantMessage]);
      setIsLoading(false);
      clearStatusMessages(targetId);
      finishRun(run);
    } catch (error) {
      if (!isRunActive(run)) return;

      setIsLoading(false);
      clearStatusMessages(targetId);
      finishRun(run);
      const assistantMessage = {
        id: generateTempId(),
        role: 'assistant',
        content: getRequestErrorMessage(error),
        chat_id: targetId,
      };
      addMessage(targetId, assistantMessage);
      await persistPlainMessages(targetId, [userMessage, assistantMessage]);
    }
  }

  async function handleProfileSelect(selectedProfile) {
    const run = startRun(chatId);

    clearPendingProfiles(chatId);
    setIsLoading(true);
    clearStatusMessages(chatId);

    try {
      await touchChatActivity(chatId);
      const result = await resumePipeline(
        chatId,
        threadIds[chatId],
        selectedProfile
      );

      if (!isRunActive(run)) return;

      ensureReadyToStream(result);
      await startSSEStream(result.thread_id, result.resume_payload, chatId, run);
    } catch (error) {
      if (!isRunActive(run)) return;

      setIsLoading(false);
      clearStatusMessages(chatId);
      finishRun(run);
      await addAndPersistFinalError(
        chatId,
        getRequestErrorMessage(error),
        run
      );
    }
  }

  async function startSSEStream(threadId, resumePayload, targetId, run) {
    if (!isRunActive(run)) return;

    const { data } = await supabase.auth.getSession();
    const token = data.session.access_token;

    if (!isRunActive(run)) return;

    setIsStreaming(true);
    setIsLoading(false);
    clearStatusMessages(targetId);
    addStatusMessage(targetId, 'Checking GitHub profile...');

    const assistantTempId = generateTempId();
    run.assistantTempId = assistantTempId;

    addMessage(targetId, {
      id: assistantTempId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      chat_id: targetId,
    });

    const cleanup = streamChatResponse(targetId, threadId, resumePayload, token, {
      onMeta({ candidate_name, role }) {
        if (!isRunActive(run)) return;

        const candidateName = cleanMetaText(candidate_name);
        const validRole = getValidRole(role);
        const title = validRole
          ? `${candidateName} — ${validRole}`
          : candidateName;
        const normalizedTitle = normalizeChatTitle(title);

        if (!title || candidateName === 'Unknown Candidate') return;

        const currentTitle =
          useChatStore.getState().chats.find((c) => c.id === targetId)?.title ?? '';
        if (!validRole && getCurrentTitleRole(currentTitle)) return;
        if (currentTitle === normalizedTitle) return;

        updateChatTitle(targetId, normalizedTitle);
        renameChat(targetId, normalizedTitle);
      },

      onStatus(text) {
        if (!isRunActive(run) || run.hasReceivedToken) return;

        addStatusMessage(targetId, text);
        if (isGeneratingRecommendationStatus(text) && !run.generatingStatusAt) {
          run.generatingStatusAt = Date.now();
        }
      },

      onToken(char) {
        if (!isRunActive(run)) return;

        if (!run.hasReceivedToken) {
          run.hasReceivedToken = true;
          const elapsed = run.generatingStatusAt
            ? Date.now() - run.generatingStatusAt
            : GENERATING_STATUS_MIN_DISPLAY_MS;
          const remaining = Math.max(0, GENERATING_STATUS_MIN_DISPLAY_MS - elapsed);

          if (remaining > 0) {
            run.tokenHandoffUntil = Date.now() + remaining;
            run.tokenBuffer += char;
            run.tokenHandoffTimer = setTimeout(
              () => revealBufferedTokens(targetId, assistantTempId, run),
              remaining
            );
            return;
          }

          run.tokensRevealed = true;
          clearStatusMessages(targetId);
        }

        if (!run.tokensRevealed) {
          run.tokenBuffer += char;
          return;
        }

        appendAssistantContent(targetId, assistantTempId, char, run);
      },

      async onDone() {
        if (!isRunActive(run)) return;

        await waitForTokenHandoff(targetId, assistantTempId, run);
        if (!isRunActive(run)) return;

        setIsStreaming(false);
        setIsLoading(false);
        clearStatusMessages(targetId);
        cleanupRef.current = null;
        finishRun(run);

        const chatMessages =
          useChatStore.getState().messages[targetId] ?? [];
        const assistantMessage = chatMessages.find(
          (m) => m.id === assistantTempId && m.role === 'assistant'
        );

        if (!assistantMessage?.content) {
          removeAssistantMessage(targetId, assistantTempId);
          await addAndPersistFinalError(
            targetId,
            'Evaluation stopped unexpectedly. Please try again.',
            run,
            { code: 'EVALUATION_STOPPED_UNEXPECTEDLY' }
          );
          return;
        }

        useChatStore.setState((state) => {
          const chatMessages = state.messages[targetId] ?? [];
          return {
            messages: {
              ...state.messages,
              [targetId]: chatMessages.map((message) =>
                message.id === assistantTempId
                  ? {
                      ...message,
                      message_type: EVALUATION_REPORT_MESSAGE_TYPE,
                      isStreaming: false,
                    }
                  : message
              ),
            },
          };
        });

        const { error } = await supabase.from('messages').insert({
          chat_id: targetId,
          role: 'assistant',
          content: serializeAssistantMessage(
            assistantMessage,
            EVALUATION_REPORT_MESSAGE_TYPE
          ),
        });

        if (error) {
          console.warn('Failed to persist assistant message:', error.message);
          addMessageSaveWarning(targetId);
        }
      },

      async onError(errorPayload) {
        if (!isRunActive(run)) return;

        clearTokenHandoffTimer(run);
        run.tokenBuffer = '';
        setIsStreaming(false);
        setIsLoading(false);
        clearStatusMessages(targetId);
        cleanupRef.current = null;
        finishRun(run);

        useChatStore.setState((state) => {
          const chatMessages = state.messages[targetId] ?? [];
          const filtered = chatMessages.filter(
            (m) =>
              !(
                m.id === assistantTempId &&
                m.role === 'assistant' &&
                m.content === ''
              )
          );
          return {
            messages: {
              ...state.messages,
              [targetId]: filtered,
            },
          };
        });

        await addAndPersistFinalError(
          targetId,
          getStreamErrorMessage(errorPayload),
          run,
          errorPayload
        );
      },
    });

    cleanupRef.current = cleanup;
  }

  return {
    sendMessage,
    handleProfileSelect,
    stopProcessing,
    isLoading,
    isStreaming,
    statusMessages: chatId ? (statusMessagesByChat[chatId] ?? []) : [],
    hasThread,
  };
}

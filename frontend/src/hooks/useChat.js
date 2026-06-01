import { useState, useEffect, useRef } from 'react';
import { useChatStore } from '../store/chatStore';
import { useChatHistory } from './useChatHistory';
import { streamChatResponse } from '../lib/streaming';
import { followUpQuestion, uploadCV, resumePipeline } from '../lib/api';
import { generateTempId, extractGitHubUsername, normalizeChatTitle } from '../lib/chatUtils';
import {
  EVALUATION_REPORT_MESSAGE_TYPE,
  FOLLOW_UP_ANSWER_MESSAGE_TYPE,
  isEvaluationReportMessage,
  serializeAssistantMessage,
  serializeUploadMessage,
} from '../lib/messagePersistence';
import { supabase } from '../lib/supabase';

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

export function useChat(chatId) {
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [statusMessagesByChat, setStatusMessagesByChat] = useState({});

  const cleanupRef = useRef(null);
  const activeRunRef = useRef(null);
  const runIdRef = useRef(0);

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
    const text = (userText ?? '').trim();

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
    }
  }

  function hasCompletedReport(targetId) {
    const chatMessages = useChatStore.getState().messages[targetId] ?? [];

    return chatMessages.some(isEvaluationReportMessage);
  }

  async function sendPreCvGuidanceMessage(userText, targetId) {
    const text = (userText ?? '').trim();
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
    };

    runIdRef.current = run.id;
    activeRunRef.current = run;
    return run;
  }

  function isRunActive(run) {
    return !!run && activeRunRef.current?.id === run.id && !run.stopped;
  }

  function finishRun(run) {
    if (activeRunRef.current?.id === run?.id) {
      activeRunRef.current = null;
    }
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
      addMessage(targetId, {
        id: generateTempId(),
        role: 'assistant',
        content: getRequestErrorMessage(error),
        chat_id: targetId,
      });
    }
  }

  async function sendFollowUpMessage(userText, targetId, run) {
    const text = (userText ?? '').trim();
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
      addMessage(chatId, {
        id: generateTempId(),
        role: 'assistant',
        content: getRequestErrorMessage(error),
        chat_id: chatId,
      });
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
    addStatusMessage(targetId, 'Checking Github Repository...');

    const assistantTempId = generateTempId();
    run.assistantTempId = assistantTempId;

    addMessage(targetId, {
      id: assistantTempId,
      role: 'assistant',
      content: '',
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
        if (!isRunActive(run)) return;

        addStatusMessage(targetId, text);
      },

      onToken(char) {
        if (!isRunActive(run)) return;

        useChatStore.setState((state) => {
          if (!isRunActive(run)) return;

          const chatMessages = state.messages[targetId];
          if (!chatMessages || chatMessages.length === 0) return;

          const assistantIndex = chatMessages.findIndex(
            (m) => m.id === assistantTempId
          );
          if (assistantIndex === -1) return;

          const assistantMessage = chatMessages[assistantIndex];
          if (assistantMessage.role !== 'assistant') return;

          const updated = {
            ...assistantMessage,
            content: assistantMessage.content + char,
          };
          const updatedMessages = [...chatMessages];
          updatedMessages[assistantIndex] = updated;

          return {
            messages: {
              ...state.messages,
              [targetId]: updatedMessages,
            },
          };
        });
      },

      async onDone() {
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
          addMessage(targetId, {
            id: generateTempId(),
            role: 'assistant',
            content: 'Evaluation stopped unexpectedly. Please try again.',
            chat_id: targetId,
          });
          return;
        }

        useChatStore.setState((state) => {
          const chatMessages = state.messages[targetId] ?? [];
          return {
            messages: {
              ...state.messages,
              [targetId]: chatMessages.map((message) =>
                message.id === assistantTempId
                  ? { ...message, message_type: EVALUATION_REPORT_MESSAGE_TYPE }
                  : message
              ),
            },
          };
        });

        await supabase.from('messages').insert({
          chat_id: targetId,
          role: 'assistant',
          content: serializeAssistantMessage(
            assistantMessage,
            EVALUATION_REPORT_MESSAGE_TYPE
          ),
        });
      },

      onError(errorPayload) {
        if (!isRunActive(run)) return;

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

        addMessage(targetId, {
          id: generateTempId(),
          role: 'assistant',
          content: getStreamErrorMessage(errorPayload),
          chat_id: targetId,
        });
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

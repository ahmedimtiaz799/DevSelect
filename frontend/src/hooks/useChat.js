import { useState, useEffect, useRef } from 'react';
import { useChatStore } from '../store/chatStore';
import { useChatHistory } from './useChatHistory';
import { streamChatResponse } from '../lib/streaming';
import { uploadCV, resumePipeline } from '../lib/api';
import { generateTempId, extractGitHubUsername } from '../lib/chatUtils';
import { supabase } from '../lib/supabase';

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

  const { renameChat } = useChatHistory();

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
    }

    if (run?.assistantTempId) {
      removeAssistantMessage(run.chatId, run.assistantTempId);
    }

    activeRunRef.current = null;
  }

  async function sendMessage(file, userText, overrideChatId) {
    const targetId = overrideChatId ?? chatId;
    const threadExists = hasThread(targetId);

    if (!file && !threadExists) return;

    const run = startRun(targetId);
    setIsLoading(true);
    clearStatusMessages(targetId);

    const tempId = generateTempId();
    addMessage(targetId, {
      id: tempId,
      role: 'user',
      ...getUserMessagePayload(file, userText),
      chat_id: targetId,
    });

    if (!file && threadExists) {
      await sendFollowUpMessage(userText, targetId, run);
      return;
    }

    try {
      const response = await uploadCV(targetId, file, threadIds[targetId]);

      if (!isRunActive(run)) return;

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
    const threadId = threadIds[targetId];
    if (!threadId) return;

    setIsLoading(true);
    clearStatusMessages(targetId);

    try {
      const result = await resumePipeline(targetId, threadId, null, userText);
      if (!isRunActive(run)) return;

      ensureReadyToStream(result);
      await startSSEStream(
        result.thread_id,
        result.resume_payload,
        targetId,
        run
      );
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

  async function handleProfileSelect(selectedProfile) {
    const run = startRun(chatId);

    clearPendingProfiles(chatId);
    setIsLoading(true);
    clearStatusMessages(chatId);

    try {
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

        const title =
          candidate_name && role
            ? `${candidate_name} — ${role}`
            : candidate_name ?? null;

        if (!title) return;

        updateChatTitle(targetId, title);
        renameChat(targetId, title);
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

        await supabase.from('messages').insert({
          chat_id: targetId,
          role: 'assistant',
          content: assistantMessage.content,
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

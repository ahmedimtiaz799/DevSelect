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

  const cleanupRef = useRef(null);

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

  async function sendMessage(file, userText, overrideChatId) {
    const targetId = overrideChatId ?? chatId;
    const threadExists = hasThread(targetId);

    if (!file && !threadExists) return;

    const tempId = generateTempId();
    addMessage(targetId, {
      id: tempId,
      role: 'user',
      content: userText,
      chat_id: targetId,
    });

    if (!file && threadExists) {
      await sendFollowUpMessage(userText, targetId);
      return;
    }

    setIsLoading(true);

    try {
      const response = await uploadCV(targetId, file, threadIds[targetId]);

      setIsLoading(false);

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
          await startSSEStream(result.thread_id, result.resume_payload, targetId);
          return;
        }

        const cleanProfiles = uniqueUsernames.map(
          (username) => `https://github.com/${username}`
        );
        setPendingProfiles(targetId, cleanProfiles);
        return;
      }

      if (response.status === 200) {
        setThreadId(targetId, response.data.thread_id);
        await startSSEStream(
          response.data.thread_id,
          response.data.resume_payload,
          targetId
        );
      }
    } catch (err) {
      setIsLoading(false);
      addMessage(targetId, {
        id: generateTempId(),
        role: 'assistant',
        content: 'Evaluation failed. Please try again.',
        chat_id: targetId,
      });
    }
  }

  async function sendFollowUpMessage(userText, targetId) {
    const threadId = threadIds[targetId];
    if (!threadId) return;

    setIsLoading(true);

    try {
      const result = await resumePipeline(targetId, threadId, null, userText);
      setIsLoading(false);
      await startSSEStream(result.thread_id, result.resume_payload, targetId);
    } catch (err) {
      setIsLoading(false);
      addMessage(targetId, {
        id: generateTempId(),
        role: 'assistant',
        content: 'Something went wrong. Please try again.',
        chat_id: targetId,
      });
    }
  }

  async function handleProfileSelect(selectedProfile) {
    clearPendingProfiles(chatId);

    try {
      const result = await resumePipeline(
        chatId,
        threadIds[chatId],
        selectedProfile
      );

      await startSSEStream(result.thread_id, result.resume_payload, chatId);
    } catch (err) {
      addMessage(chatId, {
        id: generateTempId(),
        role: 'assistant',
        content: 'Evaluation failed. Please try again.',
        chat_id: chatId,
      });
    }
  }

  async function startSSEStream(threadId, resumePayload, targetId) {
    const { data } = await supabase.auth.getSession();
    const token = data.session.access_token;

    setIsStreaming(true);

    const assistantTempId = generateTempId();
    addMessage(targetId, {
      id: assistantTempId,
      role: 'assistant',
      content: '',
      chat_id: targetId,
    });

    const cleanup = streamChatResponse(targetId, threadId, resumePayload, token, {
      onMeta({ candidate_name, role }) {
        const title =
          candidate_name && role
            ? `${candidate_name} — ${role}`
            : candidate_name ?? null;

        if (!title) return;

        updateChatTitle(targetId, title);
        renameChat(targetId, title);
      },

      onStatus(text) {
        addMessage(targetId, {
          id: generateTempId(),
          role: 'status',
          content: text,
          chat_id: targetId,
        });
      },

      onToken(char) {
        useChatStore.setState((state) => {
          const chatMessages = state.messages[targetId];
          if (!chatMessages || chatMessages.length === 0) return;

          const lastIndex = chatMessages.length - 1;
          const last = chatMessages[lastIndex];
          if (last.role !== 'assistant') return;

          const updated = { ...last, content: last.content + char };
          const updatedMessages = [...chatMessages];
          updatedMessages[lastIndex] = updated;

          return {
            messages: {
              ...state.messages,
              [targetId]: updatedMessages,
            },
          };
        });
      },

      async onDone() {
        setIsStreaming(false);
        cleanupRef.current = null;

        const chatMessages =
          useChatStore.getState().messages[targetId] ?? [];
        const lastAssistant = [...chatMessages]
          .reverse()
          .find((m) => m.role === 'assistant');

        if (lastAssistant?.content) {
          await supabase.from('messages').insert({
            chat_id: targetId,
            role: 'assistant',
            content: lastAssistant.content,
          });
        }
      },

      onError(message) {
        setIsStreaming(false);
        cleanupRef.current = null;

        useChatStore.setState((state) => {
          const chatMessages = state.messages[targetId] ?? [];
          const filtered = chatMessages.filter(
            (m) => !(m.role === 'assistant' && m.content === '')
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
          content: 'Evaluation failed. Please try again.',
          chat_id: targetId,
        });
      },
    });

    cleanupRef.current = cleanup;
  }

  return {
    sendMessage,
    handleProfileSelect,
    isLoading,
    isStreaming,
    hasThread,
  };
}
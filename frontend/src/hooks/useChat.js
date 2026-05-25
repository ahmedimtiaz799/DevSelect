import { useState, useEffect, useRef } from 'react';
import { useChatStore } from '../store/chatStore';
import { useChatHistory } from './useChatHistory';
import { streamChatResponse } from '../lib/streaming';
import { uploadCV, resumePipeline } from '../lib/api';
import { generateTempId } from '../lib/chatUtils';
import { supabase } from '../lib/supabase';

export function useChat(chatId) {
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  const cleanupRef = useRef(null);

  const messages = useChatStore((s) => s.messages);
  const threadIds = useChatStore((s) => s.threadIds);
  const pendingProfiles = useChatStore((s) => s.pendingProfiles);
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

  async function sendMessage(file, userText) {
    if (!file) return;

    const tempId = generateTempId();
    addMessage(chatId, {
      id: tempId,
      role: 'user',
      content: userText,
      chat_id: chatId,
    });

    setIsLoading(true);

    try {
      const response = await uploadCV(chatId, file, threadIds[chatId]);

      setIsLoading(false);

      if (response.status === 202) {
        setThreadId(chatId, response.data.thread_id);
        setPendingProfiles(chatId, response.data.profiles);
        return;
      }

      if (response.status === 200) {
        setThreadId(chatId, response.data.thread_id);
        await startSSEStream(
          response.data.thread_id,
          response.data.resume_payload
        );
      }
    } catch (err) {
      setIsLoading(false);
      addMessage(chatId, {
        id: generateTempId(),
        role: 'assistant',
        content: 'Evaluation failed. Please try again.',
        chat_id: chatId,
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

      await startSSEStream(result.thread_id, result.resume_payload);
    } catch (err) {
      addMessage(chatId, {
        id: generateTempId(),
        role: 'assistant',
        content: 'Evaluation failed. Please try again.',
        chat_id: chatId,
      });
    }
  }

  async function startSSEStream(threadId, resumePayload) {
    const { data } = await supabase.auth.getSession();
    const token = data.session.access_token;

    setIsStreaming(true);

    const assistantTempId = generateTempId();
    addMessage(chatId, {
      id: assistantTempId,
      role: 'assistant',
      content: '',
      chat_id: chatId,
    });

    const cleanup = streamChatResponse(chatId, threadId, resumePayload, token, {
      onMeta({ candidate_name, role }) {
        const currentTitle = useChatStore
          .getState()
          .chats.find((c) => c.id === chatId)?.title;

        const isDefaultTitle =
          !currentTitle ||
          currentTitle === 'New Chat' ||
          currentTitle === '';

        if (!isDefaultTitle) return;

        const title =
          candidate_name && role
            ? `${candidate_name} — ${role}`
            : candidate_name ?? 'New Evaluation';

        updateChatTitle(chatId, title);
        renameChat(chatId, title);
      },

      onStatus(text) {
        addMessage(chatId, {
          id: generateTempId(),
          role: 'status',
          content: text,
          chat_id: chatId,
        });
      },

      onToken(char) {
        useChatStore.setState((state) => {
          const chatMessages = state.messages[chatId];
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
              [chatId]: updatedMessages,
            },
          };
        });
      },

      async onDone() {
        setIsStreaming(false);
        cleanupRef.current = null;

        const chatMessages =
          useChatStore.getState().messages[chatId] ?? [];
        const lastAssistant = [...chatMessages]
          .reverse()
          .find((m) => m.role === 'assistant');

        if (lastAssistant?.content) {
          await supabase.from('messages').insert({
            chat_id: chatId,
            role: 'assistant',
            content: lastAssistant.content,
          });
        }
      },

      onError(message) {
        setIsStreaming(false);
        cleanupRef.current = null;

        useChatStore.setState((state) => {
          const chatMessages = state.messages[chatId] ?? [];
          const filtered = chatMessages.filter(
            (m) => !(m.role === 'assistant' && m.content === '')
          );
          return {
            messages: {
              ...state.messages,
              [chatId]: filtered,
            },
          };
        });

        addMessage(chatId, {
          id: generateTempId(),
          role: 'assistant',
          content: 'Evaluation failed. Please try again.',
          chat_id: chatId,
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
  };
}
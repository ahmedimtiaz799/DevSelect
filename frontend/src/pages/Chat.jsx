import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Sidebar } from '../components/chat/Sidebar'
import { ChatHeader } from '../components/chat/ChatHeader'
import { MessageList } from '../components/chat/MessageList'
import { InputBar } from '../components/chat/InputBar'
import { useChat } from '../hooks/useChat'
import { useFileUpload } from '../hooks/useFileUpload'
import { useChatStore } from '../store/chatStore'
import { useChatHistory } from '../hooks/useChatHistory'
import {
  isEvaluationReportMessage,
  normalizePersistedMessage,
} from '../lib/messagePersistence'
import { supabase } from '../lib/supabase'

export function Chat() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [loadedMessagesByChat, setLoadedMessagesByChat] = useState({})
  const [secondEvaluationDraft, setSecondEvaluationDraft] = useState(null)
  const [isStartingNewEvaluation, setIsStartingNewEvaluation] = useState(false)

  const navigate = useNavigate()
  const { chatId } = useParams()

  const setActiveChatId = useChatStore((s) => s.setActiveChatId)
  const setMessages = useChatStore((s) => s.setMessages)
  const pendingProfiles = useChatStore((s) => s.pendingProfiles)
  const activeMessages = useChatStore((s) => chatId ? s.messages[chatId] ?? [] : [])

  const profiles = pendingProfiles[chatId] ?? []
  const hasCompletedEvaluationReport = activeMessages.some(isEvaluationReportMessage)

  const { createNewChat } = useChatHistory()
  const sendMessageRef = useRef(null)
  const stopRequestedRef = useRef(false)

  const {
    sendMessage,
    handleProfileSelect,
    isLoading,
    isStreaming,
    statusMessages,
    stopProcessing,
    hasThread,
  } = useChat(chatId)

  const {
    file,
    error,
    onFileSelect,
    clearFile,
  } = useFileUpload(chatId)

  useEffect(() => {
    sendMessageRef.current = sendMessage
  }, [sendMessage])

  useEffect(() => {
    if (chatId) {
      setActiveChatId(chatId)
      let ignore = false

      async function fetchMessages() {
        try {
          const { data, error } = await supabase
            .from('messages')
            .select('*')
            .eq('chat_id', chatId)
            .order('created_at', { ascending: true })

          if (!ignore && !error && data) {
            const currentMessages =
              useChatStore.getState().messages[chatId] ?? []
            const hasOptimisticMessages = currentMessages.some((message) =>
              String(message.id).startsWith('temp_')
            )

            if (hasOptimisticMessages) return

            setMessages(
              chatId,
              data.filter((message) =>
                message.role === 'user' || message.role === 'assistant'
              ).map(normalizePersistedMessage)
            )
          }
        } finally {
          if (!ignore) {
            setLoadedMessagesByChat((prev) => ({
              ...prev,
              [chatId]: true,
            }))
          }
        }
      }

      fetchMessages()

      return () => {
        ignore = true
      }
    } else {
      setActiveChatId(null)
    }
  }, [chatId, setActiveChatId, setMessages])

  const isHydratingMessages =
    Boolean(chatId) && !loadedMessagesByChat[chatId]

  function getNewChatTitle(text, fileToSend) {
    return text.trim()
      ? text.trim()
      : fileToSend?.name.replace(/\.pdf$/i, '') ?? 'New Chat'
  }

  async function startEvaluationInNewChat(text, fileToSend, options = {}) {
    const targetChatId = await createNewChat(getNewChatTitle(text, fileToSend))

    if (!targetChatId) return null

    if (options.replace) {
      navigate(`/chat/${targetChatId}`, { replace: true })
    }

    await new Promise((resolve) => setTimeout(resolve, 50))

    if (stopRequestedRef.current) return null

    await sendMessageRef.current(fileToSend, text, targetChatId)
    return targetChatId
  }

  async function handleSend(text, fileToSend) {
    stopRequestedRef.current = false

    if (fileToSend && chatId && hasCompletedEvaluationReport) {
      setSecondEvaluationDraft({ text, file: fileToSend })
      return
    }

    if (!chatId) {
      await startEvaluationInNewChat(text, fileToSend, { replace: true })
      return
    }

    await sendMessageRef.current(fileToSend, text, chatId)
  }

  function handleCancelSecondEvaluation() {
    if (isStartingNewEvaluation) return
    setSecondEvaluationDraft(null)
  }

  async function handleStartSecondEvaluation() {
    if (!secondEvaluationDraft || isStartingNewEvaluation) return

    setIsStartingNewEvaluation(true)
    stopRequestedRef.current = false

    try {
      const targetChatId = await startEvaluationInNewChat(
        secondEvaluationDraft.text,
        secondEvaluationDraft.file
      )

      if (targetChatId) {
        setSecondEvaluationDraft(null)
      }
    } finally {
      setIsStartingNewEvaluation(false)
    }
  }

  function handleStop() {
    stopRequestedRef.current = true
    stopProcessing()
  }

  return (
    <div className="flex h-dvh bg-white overflow-hidden overflow-x-hidden">
      <Sidebar
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed((prev) => !prev)}
      />

      <div
        className={`flex flex-col flex-1 min-h-0 min-w-0 bg-white transition-all duration-300 ${
          isCollapsed ? 'md:ml-16' : 'md:ml-64'
        }`}
      >
        <ChatHeader chatId={chatId ?? null} onMenuClick={() => setMobileOpen(true)} />

        <MessageList
          chatId={chatId ?? null}
          isLoading={isLoading}
          isStreaming={isStreaming}
          isMessagesLoading={isHydratingMessages}
          statuses={statusMessages}
          profiles={profiles}
          onProfileSelect={handleProfileSelect}
        />

        <div className="shrink-0 bg-white pt-2 pb-4">
          <InputBar
            chatId={chatId ?? 'new'}
            onSend={handleSend}
            onStop={handleStop}
            onFileSelect={onFileSelect}
            onFileClear={clearFile}
            isLoading={isLoading}
            isStreaming={isStreaming}
            file={file}
            threadExists={hasThread(chatId)}
            hasCompletedReport={hasCompletedEvaluationReport}
            fileError={error}
          />
        </div>
      </div>

      {secondEvaluationDraft && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4">
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="new-evaluation-title"
            className="w-full max-w-md rounded-xl bg-white p-5 shadow-xl ring-1 ring-gray-200"
          >
            <h2
              id="new-evaluation-title"
              className="text-lg font-semibold text-brand-dark"
            >
              Start a new evaluation?
            </h2>

            <p className="mt-3 text-sm leading-6 text-brand-body">
              This chat already has a completed candidate report. To keep follow-up answers accurate, a new CV should start in a separate chat.
            </p>

            <p className="mt-2 text-sm leading-6 text-brand-muted">
              Your current report will stay saved in this chat.
            </p>

            <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                onClick={handleCancelSecondEvaluation}
                disabled={isStartingNewEvaluation}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Cancel
              </button>

              <button
                type="button"
                onClick={handleStartSecondEvaluation}
                disabled={isStartingNewEvaluation}
                className="rounded-lg bg-brand-dark px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-dark/90 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isStartingNewEvaluation ? 'Starting...' : 'Start new evaluation'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

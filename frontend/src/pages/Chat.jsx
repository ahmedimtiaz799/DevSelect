import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Sidebar } from '../components/chat/Sidebar'
import { ChatHeader } from '../components/chat/ChatHeader'
import { MessageList } from '../components/chat/MessageList'
import { InputBar } from '../components/chat/InputBar'
import { GitHubProfileSelector } from '../components/chat/GitHubProfileSelector'
import { useChat } from '../hooks/useChat'
import { useFileUpload } from '../hooks/useFileUpload'
import { useChatStore } from '../store/chatStore'
import { useChatHistory } from '../hooks/useChatHistory'
import { normalizePersistedMessage } from '../lib/messagePersistence'
import { supabase } from '../lib/supabase'

export function Chat() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [loadedMessagesByChat, setLoadedMessagesByChat] = useState({})

  const navigate = useNavigate()
  const { chatId } = useParams()

  const setActiveChatId = useChatStore((s) => s.setActiveChatId)
  const activeChatId = useChatStore((s) => s.activeChatId)
  const setMessages = useChatStore((s) => s.setMessages)
  const pendingProfiles = useChatStore((s) => s.pendingProfiles)

  const profiles = pendingProfiles[chatId] ?? []

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

  const messageListChatId = activeChatId ?? chatId
  const isHydratingMessages =
    Boolean(messageListChatId) && !loadedMessagesByChat[messageListChatId]

  async function handleSend(text, fileToSend) {
    stopRequestedRef.current = false

    if (!fileToSend && !hasThread(chatId)) return

    let targetChatId = chatId

    if (!targetChatId) {
      const tempTitle = text.trim()
        ? text.trim()
        : fileToSend.name.replace(/\.pdf$/i, '')

      targetChatId = await createNewChat(tempTitle)

      if (!targetChatId) return

      navigate(`/chat/${targetChatId}`, { replace: true })

      await new Promise((resolve) => setTimeout(resolve, 50))

      if (stopRequestedRef.current) return
    }

    await sendMessageRef.current(fileToSend, text, targetChatId)
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
        <ChatHeader onMenuClick={() => setMobileOpen(true)} />

        <MessageList
          isLoading={isLoading}
          isStreaming={isStreaming}
          isMessagesLoading={isHydratingMessages}
          statuses={statusMessages}
        />

        <div className="shrink-0 bg-white pt-2 pb-4">
          {profiles.length > 0 && (
            <GitHubProfileSelector
              profiles={profiles}
              onSelect={handleProfileSelect}
            />
          )}

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
            fileError={error}
          />
        </div>
      </div>
    </div>
  )
}

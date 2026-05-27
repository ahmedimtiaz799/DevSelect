import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Sidebar } from '../components/chat/Sidebar'
import { ChatHeader } from '../components/chat/ChatHeader'
import { MessageList } from '../components/chat/MessageList'
import { InputBar } from '../components/chat/InputBar'
import { LoadingStates } from '../components/chat/LoadingStates'
import { GitHubProfileSelector } from '../components/chat/GitHubProfileSelector'
import { useChat } from '../hooks/useChat'
import { useFileUpload } from '../hooks/useFileUpload'
import { useChatStore } from '../store/chatStore'
import { useChatHistory } from '../hooks/useChatHistory'
import { supabase } from '../lib/supabase'

export function Chat() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)

  const { chatId } = useParams()

  const setActiveChatId = useChatStore((s) => s.setActiveChatId)
  const setMessages = useChatStore((s) => s.setMessages)
  const messagesMap = useChatStore((s) => s.messages)
  const pendingProfiles = useChatStore((s) => s.pendingProfiles)

  const messages = messagesMap[chatId] ?? []
  const profiles = pendingProfiles[chatId] ?? []

  const statusMessages = messages
    .filter((m) => m.role === 'status')
    .map((m) => m.content)

  const { createNewChat } = useChatHistory()
  const { sendMessage, handleProfileSelect, isLoading, isStreaming } = useChat(chatId)
  const { file, error, onFileSelect, clearFile } = useFileUpload(chatId)

  useEffect(() => {
    if (chatId) {
      setActiveChatId(chatId)

      async function fetchMessages() {
        const { data, error } = await supabase
          .from('messages')
          .select('*')
          .eq('chat_id', chatId)
          .order('created_at', { ascending: true })

        if (!error && data) {
          setMessages(chatId, data)
        }
      }

      fetchMessages()
    } else {
      setActiveChatId(null)
    }
  }, [chatId])

  async function handleSend(text) {
    let activeChatId = chatId

    if (!activeChatId) {
      activeChatId = await createNewChat()
    }

    await sendMessage(file, text)
    clearFile()
  }

  function handleStop() {
  }

  return (
    <div className="flex h-dvh bg-white overflow-hidden overflow-x-hidden">
      <Sidebar
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
        isCollapsed={isCollapsed}
        onToggleCollapse={() => setIsCollapsed((prev) => !prev)}
      />

      <div className={`flex flex-col flex-1 min-h-0 min-w-0 bg-white transition-all duration-300 ${isCollapsed ? 'md:ml-16' : 'md:ml-64'}`}>
        <ChatHeader onMenuClick={() => setMobileOpen(true)} />

        <MessageList />

        <div className="shrink-0 bg-white pt-2 pb-4">
          {profiles.length > 0 && (
            <GitHubProfileSelector
              profiles={profiles}
              onSelect={handleProfileSelect}
            />
          )}

          <LoadingStates
            isLoading={isLoading}
            statuses={statusMessages}
          />

          <InputBar
            onSend={handleSend}
            onStop={handleStop}
            onFileSelect={onFileSelect}
            onFileClear={clearFile}
            isLoading={isLoading}
            isStreaming={isStreaming}
            file={file}
          />
        </div>

      </div>
    </div>
  )
}
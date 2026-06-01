import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { useChatStore } from '../store/chatStore'
import { useAuth } from './useAuth'
import { truncateTitle } from '../lib/chatUtils'

export function useChatHistory() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const {
    chats,
    setChats,
    addChat,
    updateChatTitle,
    touchChat,
    deleteChat: deleteChatFromStore,
    pinChat: pinChatInStore,
    setActiveChatId,
    activeChatId,
  } = useChatStore()

  useEffect(() => {
    if (!user) return

    async function fetchChats() {
      const { data, error } = await supabase
        .from('chats')
        .select('*')
        .eq('user_id', user.id)
        .order('updated_at', { ascending: false })

      if (error) return

      setChats(data)
    }

    fetchChats()
  }, [user, setChats])

  async function createNewChat(firstMessage) {
    const title = firstMessage ? truncateTitle(firstMessage, 40) : 'New Chat'

    const { data, error } = await supabase
      .from('chats')
      .insert({ user_id: user.id, title })
      .select()
      .single()

    if (error) return null

    addChat(data)
    setActiveChatId(data.id)
    navigate(`/chat/${data.id}`)
    return data.id
  }

  async function deleteChat(chatId) {
    const { error } = await supabase
      .from('chats')
      .delete()
      .eq('id', chatId)

    if (error) return

    deleteChatFromStore(chatId)

    if (activeChatId === chatId) {
      navigate('/chat')
    }
  }

  async function renameChat(chatId, newTitle) {
    const { error } = await supabase
      .from('chats')
      .update({ title: newTitle })
      .eq('id', chatId)

    if (error) return

    updateChatTitle(chatId, newTitle)
  }

  async function touchChatActivity(chatId) {
    if (!chatId) return

    const updatedAt = new Date().toISOString()
    touchChat(chatId, updatedAt)

    const { data, error } = await supabase
      .from('chats')
      .update({ updated_at: updatedAt })
      .eq('id', chatId)
      .select('updated_at')
      .single()

    if (error) return

    if (data?.updated_at) {
      touchChat(chatId, data.updated_at)
    }
  }

  async function pinChat(chatId, isPinned) {
    const pinnedAt = isPinned ? new Date().toISOString() : null

    const { data, error } = await supabase
      .from('chats')
      .update({ is_pinned: isPinned, pinned_at: pinnedAt })
      .eq('id', chatId)
      .select('is_pinned,pinned_at')
      .single()

    if (error) return

    pinChatInStore(
      chatId,
      data?.is_pinned ?? isPinned,
      data?.pinned_at ?? pinnedAt
    )
  }

  return { chats, createNewChat, deleteChat, renameChat, pinChat, touchChatActivity }
}

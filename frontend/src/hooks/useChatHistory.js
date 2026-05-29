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
  }, [user])

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

  async function pinChat(chatId, isPinned) {
    const { error } = await supabase
      .from('chats')
      .update({ is_pinned: isPinned })
      .eq('id', chatId)

    if (error) return

    pinChatInStore(chatId, isPinned)
  }

  return { chats, createNewChat, deleteChat, renameChat, pinChat }
}
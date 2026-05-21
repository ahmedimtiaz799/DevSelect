import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { useChatStore } from '../store/chatStore'
import { useAuth } from './useAuth'

export function useChatHistory() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { chats, setMessages, addChat, updateChatTitle, deleteChat: deleteChatFromStore, setActiveChatId, activeChatId } = useChatStore()

  useEffect(() => {
    if (!user) return

    async function fetchChats() {
      const { data, error } = await supabase
        .from('chats')
        .select('*')
        .eq('user_id', user.id)
        .order('updated_at', { ascending: false })

      if (error) return

      data.forEach((chat) => {
        addChat(chat)
      })
    }

    fetchChats()
  }, [])

  async function createNewChat() {
    const { data, error } = await supabase
      .from('chats')
      .insert({ user_id: user.id, title: 'New Chat' })
      .select()
      .single()

    if (error) return

    addChat(data)
    setActiveChatId(data.id)
    navigate(`/chat/${data.id}`)
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

  return { chats, createNewChat, deleteChat, renameChat }
}
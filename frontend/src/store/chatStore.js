import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'

export const useChatStore = create(
  immer((set) => ({
    activeChatId: null,
    chats: [],
    messages: {},
    uploadedFiles: {},
    threadIds: {},
    pendingProfiles: {},

    setActiveChatId: (id) =>
      set((state) => {
        state.activeChatId = id
      }),

    setChats: (chats) =>
      set((state) => {
        state.chats = chats
        chats.forEach((chat) => {
          if (!state.messages[chat.id]) {
            state.messages[chat.id] = []
          }
        })
      }),

    addChat: (chat) =>
      set((state) => {
        const exists = state.chats.some((c) => c.id === chat.id)
        if (!exists) {
          state.chats.unshift(chat)
        }
        if (!state.messages[chat.id]) {
          state.messages[chat.id] = []
        }
      }),

    updateChatTitle: (chatId, title) =>
      set((state) => {
        const chat = state.chats.find((c) => c.id === chatId)
        if (chat) chat.title = title
      }),

    touchChat: (chatId, updatedAt) =>
      set((state) => {
        const chat = state.chats.find((c) => c.id === chatId)
        if (chat) chat.updated_at = updatedAt
      }),

    pinChat: (chatId, isPinned, pinnedAt = null) =>
      set((state) => {
        const chat = state.chats.find((c) => c.id === chatId)
        if (chat) {
          chat.is_pinned = isPinned
          chat.pinned_at = pinnedAt
        }
      }),

    deleteChat: (chatId) =>
      set((state) => {
        state.chats = state.chats.filter((c) => c.id !== chatId)
        delete state.messages[chatId]
        delete state.uploadedFiles[chatId]
        delete state.threadIds[chatId]
        delete state.pendingProfiles[chatId]
        if (state.activeChatId === chatId) state.activeChatId = null
      }),

    setMessages: (chatId, messages) =>
      set((state) => {
        state.messages[chatId] = messages
      }),

    addMessage: (chatId, message) =>
      set((state) => {
        if (!state.messages[chatId]) state.messages[chatId] = []
        state.messages[chatId].push(message)
      }),

    setUploadedFile: (chatId, file) =>
      set((state) => {
        state.uploadedFiles[chatId] = file
      }),

    clearUploadedFile: (chatId) =>
      set((state) => {
        delete state.uploadedFiles[chatId]
      }),

    setThreadId: (chatId, threadId) =>
      set((state) => {
        state.threadIds[chatId] = threadId
      }),

    setPendingProfiles: (chatId, profiles) =>
      set((state) => {
        state.pendingProfiles[chatId] = profiles
      }),

    clearPendingProfiles: (chatId) =>
      set((state) => {
        delete state.pendingProfiles[chatId]
      }),
  }))
)

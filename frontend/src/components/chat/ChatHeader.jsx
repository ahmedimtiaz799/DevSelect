import { Menu } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'

export function ChatHeader({ chatId, onMenuClick }) {
  const { chats } = useChatStore()

  const activeChat = chatId ? chats.find((c) => c.id === chatId) : null
  const title = activeChat?.title ?? ''

  return (
    <header className="sticky top-0 z-10 h-14 bg-white shadow-sm border-b border-gray-100 flex items-center px-4 md:px-6 gap-3 shrink-0 min-w-0 overflow-hidden">
      <button
        onClick={onMenuClick}
        className="md:hidden text-brand-iconGray"
      >
        <Menu size={22} />
      </button>

      {title && (
        <h1 className="min-w-0 max-w-full flex-1 text-logo-chat text-brand-dark font-extrabold truncate">
          {title}
        </h1>
      )}
    </header>
  )
}

import { Menu } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'

export function ChatHeader({ onMenuClick }) {
  const { activeChatId, chats } = useChatStore()

  const activeChat = chats.find((c) => c.id === activeChatId)
  const title = activeChat?.title ?? 'DevSelect'

  return (
    <header className="sticky top-0 z-10 h-14 bg-white shadow-sm border-b border-gray-100 flex items-center px-4 md:px-6 gap-3 shrink-0">
      <button
        onClick={onMenuClick}
        className="md:hidden text-brand-iconGray"
      >
        <Menu size={22} />
      </button>

      <h1 className="text-logo-chat text-brand-dark font-extrabold truncate">
        {title}
      </h1>
    </header>
  )
}
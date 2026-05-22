import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MoreHorizontal, MessageSquare } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import { truncateTitle } from '../../lib/chatUtils'
import { ChatContextMenu } from './ChatContextMenu'

export function SidebarItem({ chat, onRename, onDelete, isCollapsed }) {
  const navigate = useNavigate()
  const { activeChatId, setActiveChatId } = useChatStore()
  const [menuOpen, setMenuOpen] = useState(false)

  const isActive = activeChatId === chat.id

  function handleClick() {
    setActiveChatId(chat.id)
    navigate(`/chat/${chat.id}`)
  }

  return (
    <div
      title={isCollapsed ? chat.title : undefined}
      className={`relative group flex items-center justify-between px-2 py-2 rounded-card cursor-pointer transition-colors
        ${isActive
          ? 'bg-brand-sidebarActive text-white font-bold'
          : 'text-white/50 hover:bg-white/5'
        }
        ${isCollapsed ? 'justify-center' : ''}`}
      onClick={handleClick}
    >
      <div className={`flex items-center gap-2 min-w-0 ${isCollapsed ? 'justify-center' : ''}`}>
        <MessageSquare size={16} className="shrink-0" />

        {!isCollapsed && (
          <span
            title={chat.title}
            className="text-ui truncate max-w-[130px] whitespace-nowrap overflow-hidden"
          >
            {truncateTitle(chat.title)}
          </span>
        )}
      </div>

      {!isCollapsed && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            setMenuOpen((prev) => !prev)
          }}
          className="opacity-0 group-hover:opacity-100 transition-opacity ml-1 shrink-0"
        >
          <MoreHorizontal size={16} />
        </button>
      )}

      {menuOpen && !isCollapsed && (
        <ChatContextMenu
          chatId={chat.id}
          currentTitle={chat.title}
          onRename={onRename}
          onDelete={onDelete}
          onClose={() => setMenuOpen(false)}
        />
      )}
    </div>
  )
}
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MoreVertical } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import { truncateTitle } from '../../lib/chatUtils'
import { ChatContextMenu } from './ChatContextMenu'
import { DeleteConfirmModal } from './DeleteConfirmModal'
import { RenameModal } from './RenameModal'

export function SidebarItem({ chat, onRename, onDelete, isCollapsed }) {
  const navigate = useNavigate()
  const { activeChatId, setActiveChatId } = useChatStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showRenameModal, setShowRenameModal] = useState(false)
  const [visible, setVisible] = useState(false)

  const isActive = activeChatId === chat.id

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 10)
    return () => clearTimeout(timer)
  }, [])

  function handleClick() {
    setActiveChatId(chat.id)
    navigate(`/chat/${chat.id}`)
  }

  function handleRenameConfirm(newTitle) {
    onRename(chat.id, newTitle)
    setShowRenameModal(false)
  }

  function handleDeleteConfirm() {
    setShowDeleteModal(false)
    onDelete(chat.id)
  }

  return (
    <>
      <div
        title={isCollapsed ? chat.title : undefined}
        className={`relative group flex items-center justify-between px-2 py-2 rounded-card cursor-pointer transition-all duration-200 ease-out
          ${visible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-2'}
          ${isActive
            ? 'bg-brand-sidebarActive text-white font-bold'
            : 'text-white/50 hover:bg-white/5'
          }
          ${isCollapsed ? 'justify-center' : ''}`}
        onClick={handleClick}
      >
        <div className={`flex items-center min-w-0 flex-1 ${isCollapsed ? 'justify-center' : ''}`}>
          {!isCollapsed && (
            <span
              title={chat.title}
              className="text-ui truncate max-w-[140px] whitespace-nowrap overflow-hidden"
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
            className="opacity-0 group-hover:opacity-100 transition-opacity ml-1 shrink-0 p-0.5"
          >
            <MoreVertical size={15} />
          </button>
        )}

        {menuOpen && !isCollapsed && (
          <ChatContextMenu
            onRenameClick={() => setShowRenameModal(true)}
            onDeleteClick={() => setShowDeleteModal(true)}
            onClose={() => setMenuOpen(false)}
          />
        )}
      </div>

      {showDeleteModal && (
        <DeleteConfirmModal
          chatTitle={chat.title}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setShowDeleteModal(false)}
        />
      )}

      {showRenameModal && (
        <RenameModal
          chatTitle={chat.title}
          onConfirm={handleRenameConfirm}
          onCancel={() => setShowRenameModal(false)}
        />
      )}
    </>
  )
}
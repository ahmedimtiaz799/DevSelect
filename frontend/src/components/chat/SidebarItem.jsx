import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MoreVertical } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import { truncateTitle } from '../../lib/chatUtils'
import { ChatContextMenu } from './ChatContextMenu'
import { DeleteConfirmModal } from './DeleteConfirmModal'
import { RenameModal } from './RenameModal'

export function SidebarItem({ chat, onRename, onDelete, onPin, isCollapsed }) {
  const navigate = useNavigate()
  const { activeChatId, setActiveChatId } = useChatStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 })
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showRenameModal, setShowRenameModal] = useState(false)
  const [visible, setVisible] = useState(false)
  const menuButtonRef = useRef(null)

  const isActive = activeChatId === chat.id

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 10)
    return () => clearTimeout(timer)
  }, [])

  function handleClick() {
    setActiveChatId(chat.id)
    navigate(`/chat/${chat.id}`)
  }

  function handleMenuButtonClick(e) {
    e.stopPropagation()
    const rect = menuButtonRef.current.getBoundingClientRect()
    setMenuPosition({
      top: rect.bottom + 4,
      left: rect.right - 176,
    })
    setMenuOpen((prev) => !prev)
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
            ? 'bg-white/10 text-white font-semibold'
            : 'text-white/75 hover:bg-white/5'
          }
          ${isCollapsed ? 'justify-center' : ''}`}
        onClick={handleClick}
      >
        <div className={`flex items-center gap-1.5 min-w-0 flex-1 ${isCollapsed ? 'justify-center' : ''}`}>
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
            ref={menuButtonRef}
            onClick={handleMenuButtonClick}
            className="opacity-0 group-hover:opacity-100 transition-opacity ml-1 shrink-0 p-0.5"
          >
            <MoreVertical size={15} />
          </button>
        )}
      </div>

      {menuOpen && !isCollapsed && (
        <ChatContextMenu
          position={menuPosition}
          isPinned={chat.is_pinned}
          onPinClick={() => {
            onPin(chat.id, !chat.is_pinned)
            setMenuOpen(false)
          }}
          onRenameClick={() => {
            setShowRenameModal(true)
            setMenuOpen(false)
          }}
          onDeleteClick={() => {
            setShowDeleteModal(true)
            setMenuOpen(false)
          }}
          onClose={() => setMenuOpen(false)}
        />
      )}

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
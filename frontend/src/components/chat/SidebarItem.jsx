import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { MoreVertical } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import { normalizeChatTitle, truncateTitle } from '../../lib/chatUtils'
import { ChatContextMenu } from './ChatContextMenu'
import { DeleteConfirmModal } from './DeleteConfirmModal'
import { RenameModal } from './RenameModal'

const MENU_WIDTH = 176
const MENU_HEIGHT = 126
const MENU_GAP = 4
const VIEWPORT_PADDING = 8

export function SidebarItem({
  chat,
  onRename,
  onDelete,
  onPin,
  onNavigateRequest,
  isCollapsed,
}) {
  const navigate = useNavigate()
  const { activeChatId, setActiveChatId } = useChatStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 })
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [showRenameModal, setShowRenameModal] = useState(false)
  const [visible, setVisible] = useState(false)
  const menuButtonRef = useRef(null)

  const isActive = activeChatId === chat.id
  const chatTitle = normalizeChatTitle(chat.title)

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 10)
    return () => clearTimeout(timer)
  }, [])

  function handleClick() {
    if (onNavigateRequest) {
      onNavigateRequest(`/chat/${chat.id}`, chat.id)
      return
    }

    setActiveChatId(chat.id)
    navigate(`/chat/${chat.id}`)
  }

  function handleMenuButtonClick(e) {
    e.stopPropagation()
    const rect = menuButtonRef.current.getBoundingClientRect()
    const scrollRect = menuButtonRef.current
      .closest('[data-sidebar-scroll]')
      ?.getBoundingClientRect()
    const boundaryBottom = Math.min(
      window.innerHeight - VIEWPORT_PADDING,
      scrollRect?.bottom ?? window.innerHeight - VIEWPORT_PADDING
    )
    const spaceBelow = boundaryBottom - rect.bottom
    const rawTop =
      spaceBelow >= MENU_HEIGHT + MENU_GAP
        ? rect.bottom + MENU_GAP
        : rect.top - MENU_HEIGHT - MENU_GAP
    const maxTop = Math.max(VIEWPORT_PADDING, boundaryBottom - MENU_HEIGHT)
    const maxLeft = Math.max(
      VIEWPORT_PADDING,
      window.innerWidth - MENU_WIDTH - VIEWPORT_PADDING
    )

    setMenuPosition({
      top: Math.min(Math.max(rawTop, VIEWPORT_PADDING), maxTop),
      left: Math.min(
        Math.max(rect.right - MENU_WIDTH, VIEWPORT_PADDING),
        maxLeft
      ),
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
        title={isCollapsed ? chatTitle : undefined}
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
              title={chatTitle}
              className="text-ui truncate max-w-[140px] whitespace-nowrap overflow-hidden"
            >
              {truncateTitle(chatTitle)}
            </span>
          )}
        </div>

        {!isCollapsed && (
          <button
            ref={menuButtonRef}
            onClick={handleMenuButtonClick}
            aria-label="Open chat menu"
            className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity ml-1 shrink-0 rounded-md p-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-focusRing focus-visible:ring-offset-2 focus-visible:ring-offset-brand-dark"
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
          chatTitle={chatTitle}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setShowDeleteModal(false)}
        />
      )}

      {showRenameModal && (
        <RenameModal
          chatTitle={chatTitle}
          onConfirm={handleRenameConfirm}
          onCancel={() => setShowRenameModal(false)}
        />
      )}
    </>
  )
}

import { useEffect, useRef, useState } from 'react'
import { Pencil, Trash2 } from 'lucide-react'

export function ChatContextMenu({ chatId, currentTitle, onRename, onDelete, onClose }) {
  const ref = useRef(null)
  const [isRenaming, setIsRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState(currentTitle)

  useEffect(() => {
    function handleOutsideClick(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [onClose])

  function handleRenameSubmit() {
    if (renameValue.trim() && renameValue.trim() !== currentTitle) {
      onRename(chatId, renameValue.trim())
    }
    onClose()
  }

  function handleDelete() {
    if (window.confirm('Delete this chat?')) {
      onDelete(chatId)
    }
    onClose()
  }

  return (
    <div
      ref={ref}
      className="absolute right-0 top-6 z-50 w-36 bg-white rounded-input shadow-card border border-gray-100 overflow-hidden"
    >
      {isRenaming ? (
        <input
          autoFocus
          value={renameValue}
          onChange={(e) => setRenameValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleRenameSubmit()
            if (e.key === 'Escape') onClose()
          }}
          onBlur={handleRenameSubmit}
          className="w-full px-3 py-2 text-ui text-brand-body bg-brand-inputBg outline-none"
        />
      ) : (
        <>
          <button
            onClick={() => setIsRenaming(true)}
            className="flex items-center gap-2 w-full px-3 py-2 text-ui text-brand-body hover:bg-brand-inputBg transition-colors"
          >
            <Pencil size={13} />
            Rename
          </button>
          <button
            onClick={handleDelete}
            className="flex items-center gap-2 w-full px-3 py-2 text-ui text-red-500 hover:bg-red-50 transition-colors"
          >
            <Trash2 size={13} />
            Delete
          </button>
        </>
      )}
    </div>
  )
}
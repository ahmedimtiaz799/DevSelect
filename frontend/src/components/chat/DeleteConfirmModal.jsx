import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { normalizeChatTitle } from '../../lib/chatUtils'

export function DeleteConfirmModal({ chatTitle, onConfirm, onCancel }) {
  const cancelRef = useRef(null)
  const normalizedChatTitle = normalizeChatTitle(chatTitle)

  useEffect(() => {
    cancelRef.current?.focus()
  }, [])

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onCancel()
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onCancel])

  return createPortal(
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h3 className="text-brand-dark font-bold text-lg mb-2">
          Delete chat?
        </h3>

        <p className="text-brand-muted text-msg mb-6 break-words [overflow-wrap:anywhere]">
          "{normalizedChatTitle}" will be permanently deleted.
        </p>

        <div className="flex gap-3 justify-end">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="px-4 py-2 text-ui text-brand-body border border-gray-200 rounded-pill hover:bg-brand-inputBg transition-colors"
          >
            Cancel
          </button>

          <button
            onClick={onConfirm}
            className="px-4 py-2 text-ui text-white bg-red-600 rounded-pill hover:bg-red-700 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

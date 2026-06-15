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
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center overflow-y-auto px-4 py-4">
      <div className="bg-ds-surface rounded-2xl shadow-xl w-full max-w-sm max-h-[calc(100dvh-2rem)] overflow-y-auto p-6">
        <h3 className="text-ds-text-strong font-bold text-lg mb-2">
          Delete chat?
        </h3>

        <p className="text-ds-text-muted text-msg mb-6 break-words [overflow-wrap:anywhere]">
          "{normalizedChatTitle}" will be permanently deleted.
        </p>

        <div className="flex gap-3 justify-end">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="px-4 py-2 text-ui text-ds-text border border-ds-border rounded-pill hover:bg-ds-input transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-dsAlpha-focus-ring/70 focus-visible:ring-offset-1 focus-visible:ring-offset-ds-bg"
          >
            Cancel
          </button>

          <button
            onClick={onConfirm}
            className="px-4 py-2 text-ui text-ds-text-inverse bg-ds-danger rounded-pill hover:bg-dsAlpha-danger/90 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-dsAlpha-focus-ring/70 focus-visible:ring-offset-1 focus-visible:ring-offset-ds-bg"
          >
            Delete
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { CHAT_TITLE_MAX_LENGTH, normalizeChatTitle } from '../../lib/chatUtils'

export function RenameModal({ chatTitle, onConfirm, onCancel }) {
  const normalizedChatTitle = normalizeChatTitle(chatTitle)
  const [value, setValue] = useState(normalizedChatTitle)
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
    inputRef.current?.select()
  }, [])

  function handleSubmit() {
    const normalizedValue = normalizeChatTitle(value)

    if (normalizedValue !== normalizedChatTitle) {
      onConfirm(normalizedValue)
    } else {
      onCancel()
    }
  }

  return createPortal(
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center px-4">
      <div className="bg-ds-surface rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h3 className="text-ds-text-strong font-bold text-lg mb-4">
          Rename this chat
        </h3>

        <input
          ref={inputRef}
          value={value}
          maxLength={CHAT_TITLE_MAX_LENGTH}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSubmit()
            if (e.key === 'Escape') onCancel()
          }}
          className="w-full px-4 py-3 text-ds-text text-msg border border-ds-border rounded-input bg-ds-input outline-none focus:border-ds-accent focus:bg-ds-surface focus:shadow-sm transition-colors mb-6"
        />

        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-ui text-ds-text border border-ds-border rounded-pill hover:bg-ds-input transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-dsAlpha-focus-ring/70 focus-visible:ring-offset-1 focus-visible:ring-offset-ds-bg"
          >
            Cancel
          </button>

          <button
            onClick={handleSubmit}
            className="px-4 py-2 text-ui text-ds-text-inverse bg-ds-accent rounded-pill hover:opacity-90 transition-opacity focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-dsAlpha-focus-ring/70 focus-visible:ring-offset-1 focus-visible:ring-offset-ds-bg"
          >
            Rename
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

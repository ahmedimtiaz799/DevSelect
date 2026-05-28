import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

export function RenameModal({ chatTitle, onConfirm, onCancel }) {
  const [value, setValue] = useState(chatTitle)
  const inputRef = useRef(null)

  useEffect(() => {
    inputRef.current?.focus()
    inputRef.current?.select()
  }, [])

  function handleSubmit() {
    if (value.trim() && value.trim() !== chatTitle) {
      onConfirm(value.trim())
    } else {
      onCancel()
    }
  }

  return createPortal(
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-sm p-6">
        <h3 className="text-brand-dark font-bold text-lg mb-4">
          Rename this chat
        </h3>
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSubmit()
            if (e.key === 'Escape') onCancel()
          }}
          className="w-full px-4 py-3 text-brand-body text-msg border border-gray-200 rounded-input bg-brand-inputBg outline-none focus:border-brand-dark transition-colors mb-6"
        />
        <div className="flex gap-3 justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-ui text-brand-body border border-gray-200 rounded-pill hover:bg-brand-inputBg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            className="px-4 py-2 text-ui text-white bg-brand-dark rounded-pill hover:opacity-90 transition-opacity"
          >
            Rename
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}
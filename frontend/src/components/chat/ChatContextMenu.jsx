import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Pencil, Trash2, Pin, PinOff } from 'lucide-react'

export function ChatContextMenu({ position, onRenameClick, onDeleteClick, onPinClick, onClose, isPinned }) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 10)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    function handleOutsideClick(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [onClose])

  return createPortal(
    <div
      ref={ref}
      style={{ top: position.top, left: position.left }}
      className={`fixed z-[9999] w-44 bg-brand-dark border border-white/15 rounded-xl shadow-xl overflow-hidden transition-all duration-150 ease-out
        ${visible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}
    >
      <div className="py-1">
        <button
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation()
            onPinClick()
          }}
          className="flex items-center gap-3 w-full px-4 py-2.5 text-ui text-white/80 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 focus-visible:ring-inset"
        >
          {isPinned
            ? <PinOff size={14} className="text-white/50 shrink-0" />
            : <Pin size={14} className="text-white/50 shrink-0" />
          }
          {isPinned ? 'Unpin' : 'Pin'}
        </button>
        <div className="mx-3 h-px bg-white/15" />
        <button
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation()
            onRenameClick()
          }}
          className="flex items-center gap-3 w-full px-4 py-2.5 text-ui text-white/80 hover:text-white hover:bg-white/10 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 focus-visible:ring-inset"
        >
          <Pencil size={14} className="text-white/50 shrink-0" />
          Rename
        </button>
        <div className="mx-3 h-px bg-white/15" />
        <button
          onMouseDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation()
            onDeleteClick()
          }}
          className="flex items-center gap-3 w-full px-4 py-2.5 text-ui text-red-400 hover:text-red-300 hover:bg-red-500/15 transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60 focus-visible:ring-inset"
        >
          <Trash2 size={14} className="shrink-0" />
          Delete
        </button>
      </div>
    </div>,
    document.body
  )
}

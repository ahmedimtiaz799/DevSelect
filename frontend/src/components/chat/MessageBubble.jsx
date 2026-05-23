import { useState } from 'react'
import { Copy, Check } from 'lucide-react'

export function MessageBubble({ content }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="group flex justify-end">
      <div className="relative max-w-[85%] md:max-w-bubble bg-brand-userBubble text-brand-body rounded-bubble px-4 py-3 text-msg">
        {content}
        <button
          onClick={handleCopy}
          className="absolute -bottom-5 right-0 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          {copied
            ? <Check size={14} className="text-green-500" />
            : <Copy size={14} className="text-brand-iconGray" />
          }
        </button>
      </div>
    </div>
  )
}
import { useState } from 'react'
import { Copy, Check, FileText } from 'lucide-react'

export function MessageBubble({ content = '', fileName }) {
  const [copied, setCopied] = useState(false)
  const hasText = content.trim().length > 0
  const hasFile = !!fileName
  const isFileOnly = hasFile && !hasText
  const copyText = fileName
    ? hasText
      ? `Uploaded CV: ${fileName}\n\n${content}`
      : `Uploaded CV: ${fileName}`
    : content

  async function handleCopy() {
    await navigator.clipboard.writeText(copyText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="group flex min-w-0 max-w-full justify-end">
      <div
        className={`relative min-w-0 max-w-[85%] overflow-hidden bg-brand-userBubble text-brand-body rounded-bubble text-msg ${
          isFileOnly ? 'md:max-w-xs px-2 py-2' : 'md:max-w-bubble px-3.5 py-3'
        }`}
      >
        <div className={hasFile && hasText ? 'flex flex-col gap-2.5' : 'min-w-0'}>
          {fileName && (
            <div className="flex items-center gap-2 min-w-0 rounded-lg border border-brand-dark/10 bg-white/70 px-2.5 py-2">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-brand-dark/10 text-brand-dark">
                <FileText size={15} />
              </span>

              <span className="min-w-0">
                <span className="block truncate text-sm font-medium leading-5 text-brand-body">
                  {fileName}
                </span>
                <span className="block text-xs leading-4 text-brand-muted">
                  CV uploaded
                </span>
              </span>
            </div>
          )}

          {hasText && (
            <p className="max-w-full whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
              {content}
            </p>
          )}
        </div>

        {copyText && (
          <button
            onClick={handleCopy}
            aria-label="Copy message"
            className="absolute -bottom-5 right-0 rounded-md opacity-0 group-hover:opacity-100 focus-visible:opacity-100 transition-opacity focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-focusRing/70"
          >
            {copied
              ? <Check size={14} className="text-brand-systemText" />
              : <Copy size={14} className="text-brand-iconGray" />
            }
          </button>
        )}
      </div>
    </div>
  )
}

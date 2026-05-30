import { useRef, useState, useEffect } from 'react'
import { Plus, ArrowUp, Square, FileText, X, AlertCircle } from 'lucide-react'

export function InputBar({
  chatId,
  onSend,
  onStop,
  onFileSelect,
  onFileClear,
  isLoading,
  isStreaming,
  file,
  threadExists,
  fileError,
}) {
  const [text, setText] = useState('')
  const [fileWarning, setFileWarning] = useState(false)
  const [noFileWarning, setNoFileWarning] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const fileInputRef = useRef(null)
  const textareaRef = useRef(null)

  const draftKey = `devselect:draft:${chatId ?? 'new'}`

  const hasContent = text.trim().length > 0 || !!file
  const isProcessing = isLoading || isStreaming || isSubmitting
  const canSend = hasContent && !isProcessing

  useEffect(() => {
    try {
      const savedDraft = localStorage.getItem(draftKey)
      setText(savedDraft ?? '')
    } catch {
      setText('')
    }
  }, [draftKey])

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = 'auto'
    textarea.style.height = `${textarea.scrollHeight}px`
  }, [text])

  function handleTextChange(e) {
    const value = e.target.value
    setText(value)

    try {
      if (value.trim()) {
        localStorage.setItem(draftKey, value)
      } else {
        localStorage.removeItem(draftKey)
      }
    } catch {
      // Ignore localStorage errors silently
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (canSend) handleSend()
    }
  }

  function handleSend() {
    if (!canSend) return

    if (!file && !threadExists) {
      setNoFileWarning(true)
      setTimeout(() => setNoFileWarning(false), 3000)
      return
    }

    const textToSend = text.trim()
    const fileToSend = file

    setIsSubmitting(true)
    Promise.resolve()
      .then(() => onSend(textToSend, fileToSend))
      .finally(() => {
        setIsSubmitting(false)
      })

    if (fileToSend) {
      onFileClear()
    }

    try {
      localStorage.removeItem(draftKey)
    } catch {
      // Ignore localStorage errors silently
    }

    setText('')

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  function handleStopClick() {
    setIsSubmitting(false)
    onStop()
  }

  function handleFileChange(e) {
    const selected = e.target.files?.[0]

    if (selected) {
      if (file) {
        setFileWarning(true)
        setTimeout(() => setFileWarning(false), 3000)
        e.target.value = ''
        return
      }

      onFileSelect(selected)
      e.target.value = ''
    }
  }

  const placeholder = threadExists
    ? 'Ask a follow-up question'
    : 'Upload a CV to evaluate a candidate'

  return (
    <div className="mx-4 md:mx-12 mt-2">
      {fileError && (
        <div className="flex items-center gap-2 text-amber-700 text-sm mb-2 px-1">
          <AlertCircle size={13} className="shrink-0" />
          <span>{fileError}</span>
        </div>
      )}

      {fileWarning && (
        <div className="flex items-center gap-2 text-amber-700 text-sm mb-2 px-1">
          <AlertCircle size={13} className="shrink-0" />
          <span>You can only evaluate one CV at a time</span>
        </div>
      )}

      {noFileWarning && (
        <div className="flex items-center gap-2 text-amber-700 text-sm mb-2 px-1">
          <AlertCircle size={13} className="shrink-0" />
          <span>Please upload a CV to evaluate a candidate</span>
        </div>
      )}

      <div className="flex flex-col bg-white ring-1 ring-gray-300 shadow-lg rounded-input px-3 pt-2 pb-2">
        {file && (
          <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-200 rounded-lg px-2 py-1.5 mb-2 self-start max-w-[220px]">
            <FileText size={13} className="text-brand-iconGray shrink-0" />

            <span className="truncate text-xs text-brand-body max-w-[130px]">
              {file.name}
            </span>

            <button
              onClick={onFileClear}
              className="flex items-center justify-center min-w-[20px] min-h-[20px] ml-0.5 text-brand-iconGray hover:text-red-500 transition-colors shrink-0"
            >
              <X size={12} />
            </button>
          </div>
        )}

        <div className="flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            className="hidden"
            onChange={handleFileChange}
          />

          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center min-w-[44px] min-h-[44px] text-brand-iconGray hover:text-brand-dark transition-colors cursor-pointer shrink-0"
          >
            <Plus size={20} />
          </button>

          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            className="flex-1 bg-transparent outline-none text-base text-brand-body placeholder:text-brand-muted resize-none overflow-hidden leading-6 py-[9px]"
          />

          {isProcessing ? (
            <button
              onClick={handleStopClick}
              className="flex items-center justify-center min-w-[44px] min-h-[44px] bg-brand-dark text-white rounded-full transition-colors shrink-0"
            >
              <Square size={14} fill="white" />
            </button>
          ) : canSend ? (
            <button
              onClick={handleSend}
              className="flex items-center justify-center min-w-[44px] min-h-[44px] bg-brand-dark text-white rounded-lg transition-colors shrink-0"
            >
              <ArrowUp size={16} />
            </button>
          ) : null}
        </div>
      </div>
    </div>
  )
}

import { useRef, useState, useEffect } from 'react'
import { Plus, ArrowUp, Square, FileText, X, AlertCircle } from 'lucide-react'
import {
  MAX_USER_INPUT_CHARS,
  MAX_USER_INPUT_WARNING_CHARS,
  capUserInput,
  normalizeUserInput,
} from '../../lib/textLimits'

const LOCAL_DRAFT_USER_ID = 'local'

function getDraftKey(userId, draftScope) {
  return `devselect:draft:${userId || LOCAL_DRAFT_USER_ID}:${draftScope}`
}

function uniqueKeys(keys) {
  return [...new Set(keys.filter(Boolean))]
}

function loadDraftText(keys) {
  try {
    for (const key of keys) {
      const value = localStorage.getItem(key)
      if (value !== null) {
        const capped = capUserInput(value)
        if (capped !== value) localStorage.setItem(key, capped)
        return capped
      }
    }
  } catch {
    return ''
  }

  return ''
}

function migrateDraftText(targetKey, fallbackKeys) {
  try {
    if (localStorage.getItem(targetKey) !== null) return

    const value = loadDraftText(fallbackKeys)
    if (value) localStorage.setItem(targetKey, capUserInput(value))
  } catch {
    return
  }
}

function clearDraftText(keys) {
  try {
    keys.forEach((key) => localStorage.removeItem(key))
  } catch {
    return
  }
}

export function InputBar({
  chatId,
  draftUserId,
  onSend,
  onStop,
  onFileSelect,
  onFileClear,
  isLoading,
  isStreaming,
  file,
  threadExists,
  hasCompletedReport,
  fileError,
}) {
  const draftScope = chatId ?? 'new-chat'
  const normalizedDraftUserId = draftUserId || LOCAL_DRAFT_USER_ID
  const draftKey = getDraftKey(normalizedDraftUserId, draftScope)
  const localDraftKey = getDraftKey(LOCAL_DRAFT_USER_ID, draftScope)
  const legacyDraftKey = `devselect:draft:${draftScope === 'new-chat' ? 'new' : draftScope}`
  const draftKeys = uniqueKeys([draftKey, localDraftKey, legacyDraftKey])

  const [text, setText] = useState(() => loadDraftText(draftKeys))
  const [fileWarning, setFileWarning] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const fileInputRef = useRef(null)
  const textareaRef = useRef(null)

  const hasContent = text.trim().length > 0 || !!file
  const isProcessing = isLoading || isStreaming || isSubmitting
  const canSend = hasContent && !isProcessing
  const shouldShowCharacterCount = text.length >= MAX_USER_INPUT_WARNING_CHARS

  useEffect(() => {
    if (normalizedDraftUserId !== LOCAL_DRAFT_USER_ID) {
      migrateDraftText(draftKey, [localDraftKey, legacyDraftKey])
    }
  }, [draftKey, localDraftKey, legacyDraftKey, normalizedDraftUserId])

  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    textarea.style.height = 'auto'
    textarea.style.height = `${textarea.scrollHeight}px`
  }, [text])

  function handleTextChange(e) {
    const value = capUserInput(e.target.value)
    setText(value)

    try {
      if (value.trim()) {
        localStorage.setItem(draftKey, value)
        clearDraftText(draftKeys.filter((key) => key !== draftKey))
      } else {
        clearDraftText(draftKeys)
      }
    } catch {
      return
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

    const textToSend = normalizeUserInput(text)
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

    clearDraftText(draftKeys)
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

  const placeholder = hasCompletedReport
    ? 'Ask a follow-up about this candidate...'
    : threadExists
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
            maxLength={MAX_USER_INPUT_CHARS}
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

        {shouldShowCharacterCount && (
          <div className="mt-1 text-right text-xs text-gray-500">
            {text.length}/{MAX_USER_INPUT_CHARS}
          </div>
        )}
      </div>
    </div>
  )
}

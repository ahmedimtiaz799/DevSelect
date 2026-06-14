import { Menu } from 'lucide-react'
import { useChatStore } from '../../store/chatStore'
import { normalizeChatTitle, parseCandidateTitle } from '../../lib/chatUtils'

export function ChatHeader({
  chatId,
  isTitleLoading = false,
  isEvaluationActive = false,
  onMenuClick,
}) {
  const { chats } = useChatStore()

  const activeChat = chatId ? chats.find((c) => c.id === chatId) : null
  const title = activeChat?.title ? normalizeChatTitle(activeChat.title) : ''
  const { name, role, headerTitle } = parseCandidateTitle(title)
  const displayRole = role || (name && isEvaluationActive ? 'Detecting role…' : null)
  const displayTitle = displayRole ? `${name} · ${displayRole}` : headerTitle
  const showTitleSkeleton = Boolean(chatId) && isTitleLoading && !title

  return (
    <header className="sticky top-0 z-10 h-14 bg-ds-surface shadow-sm border-b border-ds-border-subtle flex items-center px-4 md:px-6 gap-3 shrink-0 min-w-0 overflow-hidden">
      <button
        onClick={onMenuClick}
        aria-label="Open sidebar"
        className="rounded-md text-ds-icon-muted focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-dsAlpha-focus-ring/70 md:hidden"
      >
        <Menu size={22} />
      </button>

      {title && (
        <h1
          title={displayTitle}
          className="min-w-0 max-w-full flex-1 text-logo-chat text-ds-text-strong font-extrabold truncate"
        >
          <span>{name}</span>
          {displayRole && (
            <>
              <span className="text-ds-text-muted"> · </span>
              <span className="text-ds-text-muted">{displayRole}</span>
            </>
          )}
        </h1>
      )}

      {showTitleSkeleton && (
        <div
          aria-hidden="true"
          className="h-4 w-40 max-w-[60%] rounded-full bg-ds-border-subtle animate-pulse"
        />
      )}
    </header>
  )
}

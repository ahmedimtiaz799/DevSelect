import { useChatStore } from '../../store/chatStore'
import { useAutoScroll } from '../../hooks/useAutoScroll'
import { MessageBubble } from './MessageBubble'
import { AIMessage } from './AIMessage'
import { EmptyState } from './EmptyState'
import { LoadingStates } from './LoadingStates'
import { GitHubProfileSelector } from './GitHubProfileSelector'

export function MessageList({
  chatId = null,
  isLoading = false,
  isStreaming = false,
  isMessagesLoading = false,
  statuses = [],
  profiles = [],
  onProfileSelect,
}) {
  const messages = useChatStore((s) => s.messages)
  const activeMessages = chatId
    ? (messages[chatId] ?? []).filter((message) =>
        message.role === 'user' ||
        message.role === 'assistant' ||
        message.role === 'system'
      )
    : []
  const hasProfileSelector = profiles.length > 0 && !!onProfileSelect
  const hasActivity = isLoading || isStreaming
  const containerRef = useAutoScroll(activeMessages)
  const hasMessages = activeMessages.length > 0 || hasProfileSelector
  const isEmptyIdle = !hasMessages && !hasActivity && !isMessagesLoading

  return (
    <div
      ref={containerRef}
      role="log"
      aria-live="polite"
      className={`flex-1 overflow-y-auto overflow-x-hidden bg-white px-4 md:px-8 ${
        isEmptyIdle ? '' : 'py-6 pb-[229px]'
      }`}
    >
      <div
        className={`mx-auto flex w-full max-w-chat min-w-0 flex-col ${
          isEmptyIdle ? 'min-h-full justify-center' : 'gap-6'
        }`}
      >
        {activeMessages.length === 0
          ? hasActivity
            ? (
              <LoadingStates
                isLoading={hasActivity}
                statuses={statuses}
              />
            )
            : isMessagesLoading
              ? null
              : <EmptyState />
          : (
            <>
              {activeMessages.map((msg) =>
                msg.role === 'user'
                  ? (
                    <MessageBubble
                      key={msg.id}
                      content={msg.content}
                      fileName={msg.fileName}
                      fileType={msg.fileType}
                    />
                  )
                  : <AIMessage key={msg.id} message={msg} />
              )}
              {hasProfileSelector && (
                <GitHubProfileSelector
                  profiles={profiles}
                  onSelect={onProfileSelect}
                />
              )}
              <LoadingStates
                isLoading={hasActivity}
                statuses={statuses}
              />
            </>
          )
        }
      </div>
    </div>
  )
}

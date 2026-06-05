import { useChatStore } from '../../store/chatStore'
import { useAutoScroll } from '../../hooks/useAutoScroll'
import { MessageBubble } from './MessageBubble'
import { AIMessage } from './AIMessage'
import { EmptyState } from './EmptyState'
import { LoadingStates } from './LoadingStates'
import { GitHubProfileSelector } from './GitHubProfileSelector'

function MessageHistorySkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-6 animate-pulse">
      <div className="flex justify-end">
        <div className="h-14 w-56 max-w-[75%] rounded-2xl bg-gray-100" />
      </div>

      <div className="w-full max-w-2xl space-y-3">
        <div className="h-4 w-36 rounded-full bg-gray-200" />
        <div className="h-3 w-full rounded-full bg-gray-100" />
        <div className="h-3 w-11/12 rounded-full bg-gray-100" />
        <div className="h-3 w-4/5 rounded-full bg-gray-100" />
        <div className="h-3 w-2/3 rounded-full bg-gray-100" />
      </div>
    </div>
  )
}

export function MessageList({
  chatId = null,
  isLoading = false,
  isStreaming = false,
  isChatHistoryLoading = false,
  isMessagesLoading = false,
  messageLoadError = '',
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
  const showLoadingStates = isLoading || (isStreaming && statuses.length > 0)
  const containerRef = useAutoScroll(activeMessages)
  const hasMessages = activeMessages.length > 0 || hasProfileSelector
  const hasLoadError = Boolean(messageLoadError)
  const isHydratingData = isChatHistoryLoading || isMessagesLoading
  const showMessageSkeleton =
    Boolean(chatId) &&
    activeMessages.length === 0 &&
    isMessagesLoading &&
    !hasActivity &&
    !hasLoadError
  const isEmptyIdle = !hasMessages && !hasActivity && !isHydratingData && !hasLoadError

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
        {hasLoadError && (
          <div className="w-full py-1">
            <p className="text-sm text-brand-systemText break-words [overflow-wrap:anywhere]">
              {messageLoadError}
            </p>
          </div>
        )}

        {activeMessages.length === 0
          ? hasActivity
            ? (
              <LoadingStates
                isLoading={showLoadingStates}
                statuses={statuses}
              />
            )
            : showMessageSkeleton
              ? <MessageHistorySkeleton />
            : isMessagesLoading
              ? null
              : isChatHistoryLoading
                ? null
              : hasLoadError
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
                isLoading={showLoadingStates}
                statuses={statuses}
              />
            </>
          )
        }
      </div>
    </div>
  )
}

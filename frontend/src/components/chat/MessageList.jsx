import { useChatStore } from '../../store/chatStore'
import { useAutoScroll } from '../../hooks/useAutoScroll'
import { MessageBubble } from './MessageBubble'
import { AIMessage } from './AIMessage'
import { EmptyState } from './EmptyState'
import { LoadingStates } from './LoadingStates'
import { GitHubProfileSelector } from './GitHubProfileSelector'

const ACTIVITY_MODE_EVALUATION = 'evaluation'
const ACTIVITY_MODE_FOLLOW_UP = 'follow_up'

function MessageHistorySkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-6 animate-pulse">
      <div className="flex justify-end">
        <div className="h-14 w-56 max-w-[75%] rounded-2xl bg-ds-border-subtle" />
      </div>

      <div className="w-full max-w-2xl space-y-3">
        <div className="h-4 w-36 rounded-full bg-ds-border" />
        <div className="h-3 w-full rounded-full bg-ds-border-subtle" />
        <div className="h-3 w-11/12 rounded-full bg-ds-border-subtle" />
        <div className="h-3 w-4/5 rounded-full bg-ds-border-subtle" />
        <div className="h-3 w-2/3 rounded-full bg-ds-border-subtle" />
      </div>
    </div>
  )
}

function FollowUpLoadingState() {
  return (
    <div className="w-full max-w-ai-msg py-1" aria-live="polite">
      <p className="text-ds-text-muted text-msg italic">
        Thinking...
      </p>
    </div>
  )
}

function isEmptyStreamingAssistant(message) {
  return (
    message.role === 'assistant' &&
    message.isStreaming &&
    !message.content?.trim()
  )
}

export function MessageList({
  chatId = null,
  isLoading = false,
  isStreaming = false,
  activityMode = null,
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
  const visibleMessages = activeMessages.filter(
    (message) => !isEmptyStreamingAssistant(message)
  )
  const hasProfileSelector = profiles.length > 0 && !!onProfileSelect
  const hasActivity = isLoading || isStreaming
  const isEvaluationLoading =
    activityMode === ACTIVITY_MODE_EVALUATION &&
    (isLoading || (isStreaming && statuses.length > 0))
  const isFollowUpLoading = activityMode === ACTIVITY_MODE_FOLLOW_UP && isLoading
  const autoScrollLayoutKey = [
    statuses.join('\u0001'),
    isLoading ? 'loading' : 'idle',
    isStreaming ? 'streaming' : 'static',
    hasProfileSelector ? 'profiles' : 'messages',
  ].join('\u0002')
  const containerRef = useAutoScroll(visibleMessages, autoScrollLayoutKey)
  const hasMessages = visibleMessages.length > 0 || hasProfileSelector
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
      className={`flex-1 overflow-y-auto overflow-x-hidden bg-ds-surface px-4 md:px-8 ${
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
            <p className="text-sm text-ds-text-subtle break-words [overflow-wrap:anywhere]">
              {messageLoadError}
            </p>
          </div>
        )}

        {activeMessages.length === 0
          ? hasActivity
            ? (
              isFollowUpLoading
                ? <FollowUpLoadingState />
                : (
                  <LoadingStates
                    isLoading={isEvaluationLoading}
                    statuses={statuses}
                  />
                )
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
              {visibleMessages.map((msg) =>
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
                isLoading={isEvaluationLoading}
                statuses={statuses}
              />
              {isFollowUpLoading && <FollowUpLoadingState />}
            </>
          )
        }
      </div>
    </div>
  )
}

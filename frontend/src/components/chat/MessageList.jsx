import { useChatStore } from '../../store/chatStore'
import { useAutoScroll } from '../../hooks/useAutoScroll'
import { MessageBubble } from './MessageBubble'
import { AIMessage } from './AIMessage'
import { EmptyState } from './EmptyState'
import { LoadingStates } from './LoadingStates'

export function MessageList({ isLoading = false, isStreaming = false, statuses = [] }) {
  const activeChatId = useChatStore((s) => s.activeChatId)
  const messages = useChatStore((s) => s.messages)
  const activeMessages = activeChatId
    ? (messages[activeChatId] ?? []).filter((message) =>
        message.role === 'user' ||
        message.role === 'assistant' ||
        message.role === 'system'
      )
    : []
  const hasActivity = isLoading || isStreaming
  const containerRef = useAutoScroll(activeMessages)
  const hasMessages = activeMessages.length > 0
  const isEmptyIdle = !hasMessages && !hasActivity

  return (
    <div
      ref={containerRef}
      role="log"
      aria-live="polite"
      className={`flex-1 overflow-y-auto bg-white px-4 md:px-8 ${
        isEmptyIdle ? '' : 'py-6 pb-[229px]'
      }`}
    >
      <div
        className={`mx-auto flex w-full max-w-chat flex-col ${
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

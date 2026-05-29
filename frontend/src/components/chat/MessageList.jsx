import { useChatStore } from '../../store/chatStore'
import { useAutoScroll } from '../../hooks/useAutoScroll'
import { MessageBubble } from './MessageBubble'
import { AIMessage } from './AIMessage'
import { EmptyState } from './EmptyState'

export function MessageList() {
  const activeChatId = useChatStore((s) => s.activeChatId)
  const messages = useChatStore((s) => s.messages)
  const activeMessages = activeChatId ? (messages[activeChatId] ?? []) : []
  const containerRef = useAutoScroll(activeMessages)

  return (
    <div
      ref={containerRef}
      role="log"
      aria-live="polite"
      className={`flex-1 overflow-y-auto bg-white px-4 md:px-12 py-6 flex flex-col gap-6 ${activeMessages.length > 0 ? 'pb-[229px]' : ''}`}
    >
      {activeMessages.length === 0
        ? <EmptyState />
        : activeMessages.map((msg) =>
            msg.role === 'user'
              ? <MessageBubble key={msg.id} content={msg.content} />
              : <AIMessage key={msg.id} message={msg} />
          )
      }
    </div>
  )
}
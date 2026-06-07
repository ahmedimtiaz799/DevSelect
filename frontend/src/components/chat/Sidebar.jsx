import { useState, useRef, useEffect } from 'react'
import { Search, ChevronLeft, ChevronRight, X } from 'lucide-react'
import { useChatHistory } from '../../hooks/useChatHistory'
import { SidebarItem } from './SidebarItem'
import { UserMenu } from './UserMenu'
import { normalizeChatTitle } from '../../lib/chatUtils'

function chatActivityTime(chat) {
  const value = Date.parse(chat.updated_at || chat.created_at || '')
  return Number.isNaN(value) ? 0 : value
}

function sortByLatestActivity(a, b) {
  return chatActivityTime(b) - chatActivityTime(a)
}

function dateSortValue(value) {
  const parsed = Date.parse(value || '')
  return Number.isNaN(parsed) ? 0 : parsed
}

function pinnedSortValue(chat) {
  return dateSortValue(chat.pinned_at || chat.created_at || chat.updated_at)
}

function sortByStablePinnedOrder(a, b) {
  const aValue = pinnedSortValue(a)
  const bValue = pinnedSortValue(b)

  if (aValue !== bValue) return aValue - bValue
  return String(a.id).localeCompare(String(b.id))
}

const SIDEBAR_SKELETON_WIDTHS = [
  'w-36',
  'w-28',
  'w-40',
  'w-32',
  'w-44',
  'w-24',
  'w-36',
]
const SIDEBAR_LABEL_DELAY_MS = 100

function SidebarChatSkeleton() {
  return (
    <div aria-hidden="true" className="flex flex-col gap-1 px-1 py-2 animate-pulse">
      {SIDEBAR_SKELETON_WIDTHS.map((width, index) => (
        <div
          key={index}
          className="flex items-center rounded-card px-2 py-2"
        >
          <div className={`h-3 rounded-full bg-white/10 ${width}`} />
        </div>
      ))}
    </div>
  )
}

export function Sidebar({
  mobileOpen,
  onMobileClose,
  isCollapsed,
  onToggleCollapse,
  onNavigateRequest,
}) {
  const {
    chats,
    chatListError,
    isChatListLoading,
    createNewChat,
    deleteChat,
    renameChat,
    pinChat,
  } = useChatHistory()

  const [search, setSearch] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [showExpandedLabels, setShowExpandedLabels] = useState(() => !isCollapsed)

  const searchRef = useRef(null)

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setShowExpandedLabels(!isCollapsed)
    }, isCollapsed ? 0 : SIDEBAR_LABEL_DELAY_MS)

    return () => window.clearTimeout(timeoutId)
  }, [isCollapsed])

  useEffect(() => {
    if (searchOpen) searchRef.current?.focus()
  }, [searchOpen])

  function handleSearchClose() {
    setSearchOpen(false)
    setSearch('')
  }

  function handleNewChatClick() {
    if (onNavigateRequest) {
      onNavigateRequest('/chat', null)
      return
    }

    createNewChat()
  }

  const filtered = chats.filter((c) =>
    normalizeChatTitle(c.title, '').toLowerCase().includes(search.toLowerCase())
  )

  const pinnedChats = filtered
    .filter((c) => c.is_pinned)
    .sort(sortByStablePinnedOrder)
  const unpinnedChats = filtered
    .filter((c) => !c.is_pinned)
    .sort(sortByLatestActivity)
  const expandedStructureVisible = !isCollapsed
  const expandedLabelsVisible = expandedStructureVisible && showExpandedLabels
  const hasBothSections = pinnedChats.length > 0 && unpinnedChats.length > 0
  const hasNoSearchResults =
    expandedStructureVisible &&
    search.trim().length > 0 &&
    chats.length > 0 &&
    filtered.length === 0 &&
    !isChatListLoading &&
    !chatListError
  const showChatListSkeleton =
    expandedStructureVisible && isChatListLoading && !chatListError && chats.length === 0

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={onMobileClose}
        />
      )}

      <aside
        className={`fixed top-0 left-0 h-full bg-brand-dark border-r border-white/10 flex flex-col z-30 transition-all duration-300
          ${isCollapsed ? 'w-16' : 'w-64'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0`}
      >
        <div className="px-3 pt-6 pb-4 flex flex-col gap-4">
          <div
            className={`flex items-center ${
              isCollapsed ? 'justify-center' : 'justify-between'
            }`}
          >
            {expandedStructureVisible && (
              <span
                className={`overflow-hidden whitespace-nowrap text-logo-chat text-white uppercase tracking-widest transition-opacity duration-150 ${
                  expandedLabelsVisible ? 'opacity-100' : 'opacity-0'
                }`}
              >
                DevSelect
              </span>
            )}

            <button
              onClick={onToggleCollapse}
              aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              className="hidden md:flex items-center justify-center rounded-md text-white/50 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60"
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? (
                <ChevronRight size={16} />
              ) : (
                <ChevronLeft size={16} />
              )}
            </button>
          </div>

          <div className={`flex ${isCollapsed ? 'justify-center' : ''}`}>
            <button
              onClick={handleNewChatClick}
              aria-label="New chat"
              className={`flex items-center justify-center rounded-pill border border-[#e8e4dc]/80 bg-[#f4f1ea] py-2 text-btn-sm font-semibold text-brand-dark shadow-sm shadow-black/5 transition-[background-color,border-color,box-shadow] duration-150 hover:border-[#ded8cf] hover:bg-[#ebe6dc] hover:shadow-sm hover:shadow-black/10 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-focusRing/70 focus-visible:ring-offset-1 focus-visible:ring-offset-brand-dark
                ${
                  isCollapsed
                    ? 'w-10 h-10 p-0 text-lg'
                    : 'w-full px-3'
                }`}
            >
              {isCollapsed ? (
                '+'
              ) : (
                <span
                  className={`inline-flex items-center justify-center gap-1.5 overflow-hidden whitespace-nowrap transition-opacity duration-150 ${
                    expandedLabelsVisible ? 'opacity-100' : 'opacity-0'
                  }`}
                >
                  <span aria-hidden="true" className="text-[15px] leading-none">+</span>
                  <span>New Chat</span>
                </span>
              )}
            </button>
          </div>

          {expandedStructureVisible && chats.length > 0 && (
            <div className="flex items-center">
              {searchOpen ? (
                <div className="flex items-center gap-2 bg-white/[0.07] rounded-search px-3 py-2 border border-white/30 w-full focus-within:border-white/50 focus-within:bg-white/[0.09] transition-colors">
                  <Search size={13} className="text-white/60 shrink-0" />

                  <input
                    ref={searchRef}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Escape') handleSearchClose()
                    }}
                    placeholder="Search chats..."
                    className="bg-transparent text-search text-white placeholder-white/50 outline-none w-full"
                  />

                  {search.length > 0 && (
                    <button
                      onClick={handleSearchClose}
                      aria-label="Clear chat search"
                      className="rounded-md focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60"
                    >
                      <X
                        size={13}
                        className="text-white/60 hover:text-white transition-colors"
                      />
                    </button>
                  )}
                </div>
              ) : (
                <button
                  onClick={() => setSearchOpen(true)}
                  aria-label="Search chats"
                  className="flex items-center gap-2 w-full px-3 py-2 rounded-search border border-white/20 hover:border-white/35 bg-white/[0.04] hover:bg-white/[0.07] text-white/60 hover:text-white/80 transition-all text-search focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/60"
                >
                  <Search size={14} className="shrink-0" />
                  <span
                    className={`overflow-hidden whitespace-nowrap transition-opacity duration-150 ${
                      expandedLabelsVisible ? 'opacity-100' : 'opacity-0'
                    }`}
                  >
                    Search chats...
                  </span>
                </button>
              )}
            </div>
          )}
        </div>

        <div
          data-sidebar-scroll
          className="flex-1 overflow-y-auto px-2 flex flex-col gap-1
          [&::-webkit-scrollbar]:w-[6px]
          [&::-webkit-scrollbar-track]:bg-transparent
          [&::-webkit-scrollbar-thumb]:bg-[#c4c4ce]
          [&::-webkit-scrollbar-thumb]:rounded-full
          [&::-webkit-scrollbar-thumb:hover]:bg-[#a0a0b0]"
        >
          {chatListError && expandedStructureVisible && (
            <p
              className={`px-2 py-2 text-sm leading-5 text-white/60 transition-opacity duration-150 ${
                expandedLabelsVisible ? 'opacity-100' : 'opacity-0'
              }`}
            >
              {chatListError}
            </p>
          )}

          {showChatListSkeleton && (
            <SidebarChatSkeleton />
          )}

          {hasNoSearchResults && (
            <p
              className={`px-2 py-2 text-sm leading-5 text-white/60 transition-opacity duration-150 ${
                expandedLabelsVisible ? 'opacity-100' : 'opacity-0'
              }`}
            >
              No chats match your search.
            </p>
          )}

          {expandedStructureVisible && pinnedChats.length > 0 && (
            <>
              <div className="px-2 pt-2 pb-1">
                <span
                  className={`block overflow-hidden whitespace-nowrap text-[10px] uppercase tracking-widest text-white/50 font-bold transition-opacity duration-150 ${
                    expandedLabelsVisible ? 'opacity-100' : 'opacity-0'
                  }`}
                >
                  Pinned
                </span>
              </div>

              {pinnedChats.map((chat) => (
                <SidebarItem
                  key={chat.id}
                  chat={chat}
                  onRename={renameChat}
                  onDelete={deleteChat}
                  onPin={pinChat}
                  onNavigateRequest={onNavigateRequest}
                  isCollapsed={isCollapsed}
                  labelsVisible={expandedLabelsVisible}
                />
              ))}
            </>
          )}

          {hasBothSections && expandedStructureVisible && (
            <div className="px-2 pt-2 pb-1">
              <span
                className={`block overflow-hidden whitespace-nowrap text-[10px] uppercase tracking-widest text-white/50 font-bold transition-opacity duration-150 ${
                  expandedLabelsVisible ? 'opacity-100' : 'opacity-0'
                }`}
              >
                Recent
              </span>
            </div>
          )}

          {expandedStructureVisible && unpinnedChats.map((chat) => (
            <SidebarItem
              key={chat.id}
              chat={chat}
              onRename={renameChat}
              onDelete={deleteChat}
              onPin={pinChat}
              onNavigateRequest={onNavigateRequest}
              isCollapsed={isCollapsed}
              labelsVisible={expandedLabelsVisible}
            />
          ))}
        </div>

        <div className="px-3 py-3 border-t border-white/10">
          <UserMenu isCollapsed={isCollapsed} labelsVisible={expandedLabelsVisible} />
        </div>
      </aside>
    </>
  )
}

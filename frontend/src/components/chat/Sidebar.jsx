import { useState, useRef, useEffect } from 'react'
import { Search, LogOut, ChevronLeft, ChevronRight, X } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { useChatHistory } from '../../hooks/useChatHistory'
import { SidebarItem } from './SidebarItem'

export function Sidebar({ mobileOpen, onMobileClose, isCollapsed, onToggleCollapse }) {
  const { signOut } = useAuth()
  const { chats, createNewChat, deleteChat, renameChat, pinChat } = useChatHistory()
  const [search, setSearch] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const searchRef = useRef(null)

  useEffect(() => {
    if (searchOpen) searchRef.current?.focus()
  }, [searchOpen])

  function handleSearchClose() {
    setSearchOpen(false)
    setSearch('')
  }

  const filtered = chats.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  )

  const pinnedChats = filtered.filter((c) => c.is_pinned)
  const unpinnedChats = filtered.filter((c) => !c.is_pinned)
  const hasBothSections = pinnedChats.length > 0 && unpinnedChats.length > 0

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
          <div className={`flex items-center ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
            {!isCollapsed && (
              <span className="text-logo-chat text-white uppercase tracking-widest">
                DevSelect
              </span>
            )}
            <button
              onClick={onToggleCollapse}
              className="hidden md:flex items-center justify-center text-white/50 hover:text-white transition-colors"
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            </button>
          </div>

          <div className={`flex ${isCollapsed ? 'justify-center' : ''}`}>
            <button
              onClick={() => createNewChat()}
              className={`bg-white text-brand-dark text-btn-sm font-semibold rounded-pill py-2 hover:bg-gray-100 transition-colors
                ${isCollapsed ? 'w-10 h-10 flex items-center justify-center p-0 text-lg' : 'w-full'}`}
            >
              {isCollapsed ? '+' : '+ New Chat'}
            </button>
          </div>

          {!isCollapsed && chats.length > 0 && (
            <div className="flex items-center">
              {searchOpen ? (
                <div className="flex items-center gap-2 bg-white/[0.07] rounded-search px-3 py-2 border border-white/30 w-full focus-within:border-white/50 transition-colors">
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
                    <button onClick={handleSearchClose}>
                      <X size={13} className="text-white/60 hover:text-white transition-colors" />
                    </button>
                  )}
                </div>
              ) : (
                <button
                  onClick={() => setSearchOpen(true)}
                  className="flex items-center gap-2 w-full px-3 py-2 rounded-search border border-white/20 hover:border-white/35 bg-white/[0.04] hover:bg-white/[0.07] text-white/60 hover:text-white/80 transition-all text-search"
                >
                  <Search size={14} className="shrink-0" />
                  <span>Search chats...</span>
                </button>
              )}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-2 flex flex-col gap-1
          [&::-webkit-scrollbar]:w-[6px]
          [&::-webkit-scrollbar-track]:bg-transparent
          [&::-webkit-scrollbar-thumb]:bg-[#c4c4ce]
          [&::-webkit-scrollbar-thumb]:rounded-full
          [&::-webkit-scrollbar-thumb:hover]:bg-[#a0a0b0]">

          {pinnedChats.length > 0 && (
            <>
              {!isCollapsed && (
                <div className="px-2 pt-2 pb-1">
                  <span className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">
                    Pinned
                  </span>
                </div>
              )}
              {pinnedChats.map((chat) => (
                <SidebarItem
                  key={chat.id}
                  chat={chat}
                  onRename={renameChat}
                  onDelete={deleteChat}
                  onPin={pinChat}
                  isCollapsed={isCollapsed}
                />
              ))}
            </>
          )}

          {hasBothSections && !isCollapsed && (
            <div className="px-2 pt-2 pb-1">
              <span className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold">
                Recent
              </span>
            </div>
          )}

          {unpinnedChats.map((chat) => (
            <SidebarItem
              key={chat.id}
              chat={chat}
              onRename={renameChat}
              onDelete={deleteChat}
              onPin={pinChat}
              isCollapsed={isCollapsed}
            />
          ))}
        </div>

        <div className="px-3 py-4 border-t border-white/10 flex justify-start items-center">
          <button
            onClick={signOut}
            className="flex items-center gap-2 text-white/80 hover:text-white text-ui transition-colors"
            title="Log out"
          >
            <LogOut size={16} />
            {!isCollapsed && 'Log out'}
          </button>
        </div>
      </aside>
    </>
  )
}
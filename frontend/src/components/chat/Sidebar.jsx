import { useState } from 'react'
import { Search, LogOut, ChevronLeft, ChevronRight } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth'
import { useChatHistory } from '../../hooks/useChatHistory'
import { SidebarItem } from './SidebarItem'

export function Sidebar({ mobileOpen, onMobileClose }) {
  const { signOut } = useAuth()
  const { chats, createNewChat, deleteChat, renameChat } = useChatHistory()
  const [search, setSearch] = useState('')
  const [isCollapsed, setIsCollapsed] = useState(false)

  const filtered = chats.filter((c) =>
    c.title.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={onMobileClose}
        />
      )}

      <aside
        className={`fixed top-0 left-0 h-full bg-brand-dark flex flex-col z-30 transition-all duration-300
          ${isCollapsed ? 'w-16' : 'w-64'}
          ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0`}
      >
        <div className={`px-3 pt-6 pb-4 flex flex-col gap-4 ${isCollapsed ? 'items-center' : ''}`}>
          {!isCollapsed && (
            <span className="text-logo-chat text-white uppercase tracking-widest">
              DevSelect
            </span>
          )}

          <button
            onClick={createNewChat}
            className={`bg-white text-brand-dark text-btn-sm font-semibold rounded-pill py-2 hover:opacity-90 transition-opacity
              ${isCollapsed ? 'w-10 h-10 flex items-center justify-center p-0 text-lg' : 'w-full'}`}
          >
            {isCollapsed ? '+' : '+ New Chat'}
          </button>

          {!isCollapsed && (
            <div className="flex items-center gap-2 bg-white/10 rounded-search px-3 py-2 border border-white/20">
              <Search size={14} className="text-white/40 shrink-0" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search chats..."
                className="bg-transparent text-search text-white placeholder-white/30 outline-none w-full"
              />
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-2 flex flex-col gap-1">
          {filtered.map((chat) => (
            <SidebarItem
              key={chat.id}
              chat={chat}
              onRename={renameChat}
              onDelete={deleteChat}
              isCollapsed={isCollapsed}
            />
          ))}
        </div>

        <div className={`px-3 py-4 border-t border-white/10 flex ${isCollapsed ? 'justify-center' : 'justify-between'} items-center`}>
          {!isCollapsed && (
            <button
              onClick={signOut}
              className="flex items-center gap-2 text-white/50 hover:text-white text-ui transition-colors"
            >
              <LogOut size={16} />
              Log out
            </button>
          )}

          {isCollapsed && (
            <button
              onClick={signOut}
              className="text-white/50 hover:text-white transition-colors"
              title="Log out"
            >
              <LogOut size={16} />
            </button>
          )}

          <button
            onClick={() => setIsCollapsed((prev) => !prev)}
            className="hidden md:flex items-center justify-center text-white/50 hover:text-white transition-colors"
            title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>
      </aside>
    </>
  )
}
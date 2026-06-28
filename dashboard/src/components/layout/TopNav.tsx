import React, { useState, useEffect, useRef } from 'react'
import { Bell, Search, Wifi, WifiOff, X, ArrowRight, CornerDownRight } from 'lucide-react'
import { searchEverything } from '../../api/dashboard'
import { useNotificationStore } from '../../store/notificationStore'
import type { SearchHit, NavSection } from '../../types'

interface TopNavProps {
  wsConnected: boolean
  onSelectCustomer: (id: string) => void
  onSelectConversation: (id: string) => void
  onNavigate: (section: NavSection) => void
}

export const TopNav: React.FC<TopNavProps> = ({
  wsConnected,
  onSelectCustomer,
  onSelectConversation,
  onNavigate,
}) => {
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [showHits, setShowHits] = useState(false)
  const [loading, setLoading] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)

  const notifications = useNotificationStore((s) => s.notifications)
  const unreadCount = useNotificationStore((s) => s.unreadCount)
  const markAllRead = useNotificationStore((s) => s.markAllRead)
  const clearNotifications = useNotificationStore((s) => s.clear)

  const searchRef = useRef<HTMLDivElement>(null)

  // Debounced search everything call
  useEffect(() => {
    if (query.trim().length < 2) {
      setHits([])
      return
    }

    const delay = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await searchEverything(query)
        setHits(res.hits)
      } catch (err) {
        console.error('Search failed', err)
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => clearTimeout(delay)
  }, [query])

  // Click outside search container to close results dropdown
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowHits(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  const handleHitClick = (hit: SearchHit) => {
    setShowHits(false)
    setQuery('')
    if (hit.type === 'customer') {
      onSelectCustomer(hit.id)
      onNavigate('customers')
    } else if (hit.type === 'conversation' || hit.type === 'intent') {
      onSelectConversation(hit.id)
      onNavigate('conversations')
    }
  }

  return (
    <header className="h-16 border-b border-[#334155] bg-[#1e293b] px-6 flex items-center justify-between relative z-10 shrink-0">
      {/* 1. Global Search Everything */}
      <div ref={searchRef} className="relative w-96">
        <div className="relative">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
            <Search className="h-4 w-4" />
          </span>
          <input
            type="text"
            className="input pl-10"
            placeholder="Search name, phone, email, notes, intent, message..."
            value={query}
            onFocus={() => setShowHits(true)}
            onChange={(e) => {
              setQuery(e.target.value)
              setShowHits(true)
            }}
          />
          {query && (
            <button
              onClick={() => {
                setQuery('')
                setHits([])
              }}
              className="absolute inset-y-0 right-0 flex items-center pr-3 text-slate-400 hover:text-slate-200"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Search Results Autocomplete Dropdown */}
        {showHits && query.trim().length >= 2 && (
          <div className="absolute left-0 mt-2 w-[480px] bg-[#1e293b] border border-[#334155] rounded-xl shadow-2xl overflow-hidden divide-y divide-[#334155] max-h-96 overflow-y-auto">
            <div className="px-4 py-2 text-xs font-semibold text-slate-400 bg-[#0f172a]/40 flex justify-between">
              <span>Search results ({hits.length})</span>
              {loading && <span className="animate-pulse">searching...</span>}
            </div>

            {hits.length === 0 && !loading ? (
              <div className="p-4 text-sm text-slate-400 text-center">
                No matching records found.
              </div>
            ) : (
              hits.map((hit) => (
                <button
                  key={hit.id}
                  onClick={() => handleHitClick(hit)}
                  className="w-full text-left p-3 hover:bg-[#263248] flex flex-col transition-all"
                >
                  <div className="flex items-center justify-between w-full">
                    <span className="text-sm font-semibold text-slate-200">{hit.title}</span>
                    <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/10">
                      {hit.type}
                    </span>
                  </div>
                  {hit.subtitle && (
                    <span className="text-xs text-slate-400 mt-0.5">{hit.subtitle}</span>
                  )}
                  {hit.highlight && (
                    <div className="mt-1.5 text-xs text-slate-300 italic flex items-center gap-1">
                      <CornerDownRight className="h-3 w-3 text-indigo-400 shrink-0" />
                      <span className="truncate">...{hit.highlight}...</span>
                    </div>
                  )}
                </button>
              ))
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* 2. WebSockets Connection Status */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium ${
            wsConnected
              ? 'bg-emerald-500/5 text-emerald-400 border-emerald-500/15'
              : 'bg-rose-500/5 text-rose-400 border-rose-500/15'
          }`}
        >
          {wsConnected ? (
            <>
              <Wifi className="h-3.5 w-3.5 pulse-green" />
              <span>Live Updates Active</span>
            </>
          ) : (
            <>
              <WifiOff className="h-3.5 w-3.5 text-rose-400" />
              <span>Offline</span>
            </>
          )}
        </div>

        {/* 3. Notifications Dropdown Toggle */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg relative cursor-pointer"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 h-5 w-5 bg-rose-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-bounce">
                {unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Panel */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-[#1e293b] border border-[#334155] rounded-xl shadow-2xl overflow-hidden divide-y divide-[#334155] z-50">
              <div className="px-4 py-3 bg-[#0f172a]/30 flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-200">Alert Center</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => markAllRead()}
                    className="text-[10px] text-indigo-400 hover:text-indigo-300 font-semibold uppercase"
                  >
                    Read All
                  </button>
                  <span className="text-slate-500">|</span>
                  <button
                    onClick={() => clearNotifications()}
                    className="text-[10px] text-rose-400 hover:text-rose-300 font-semibold uppercase"
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div className="max-h-72 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">
                    No active system alerts.
                  </div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`p-3 text-xs flex gap-2 transition-all hover:bg-[#263248] ${
                        n.read ? 'opacity-60' : 'bg-indigo-500/5'
                      }`}
                    >
                      <div className="mt-0.5">
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${
                            n.type === 'error'
                              ? 'bg-rose-500'
                              : n.type === 'warning'
                              ? 'bg-amber-500'
                              : n.type === 'success'
                              ? 'bg-emerald-500'
                              : 'bg-indigo-500'
                          }`}
                        />
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-slate-200">{n.title}</p>
                        <p className="text-slate-400 mt-0.5 leading-relaxed">{n.message}</p>
                        <span className="text-[10px] text-slate-500 mt-1 block">
                          {new Date(n.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

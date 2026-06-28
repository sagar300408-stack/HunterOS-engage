import React from 'react'
import {
  LayoutDashboard,
  MessageSquare,
  Users,
  Kanban,
  BarChart3,
  Activity,
  History,
  ShieldCheck,
  Cpu,
  LogOut,
  Sliders,
} from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import type { NavSection } from '../../types'

interface SidebarProps {
  currentSection: NavSection
  onSelectSection: (section: NavSection) => void
}

export const Sidebar: React.FC<SidebarProps> = ({ currentSection, onSelectSection }) => {
  const logout = useAuthStore((s) => s.logout)
  const role = useAuthStore((s) => s.role)
  const user = useAuthStore((s) => s.user)

  const menuItems = [
    { id: 'overview' as NavSection, label: 'Overview', icon: LayoutDashboard },
    { id: 'conversations' as NavSection, label: 'Live Chat Feed', icon: MessageSquare },
    { id: 'customers' as NavSection, label: 'Customers', icon: Users },
    { id: 'leads' as NavSection, label: 'Lead Pipeline', icon: Kanban },
    { id: 'analytics' as NavSection, label: 'AI Cost & Stats', icon: BarChart3 },
    { id: 'activity' as NavSection, label: 'AI Activity Feed', icon: Activity },
    { id: 'queue' as NavSection, label: 'Queue Monitor', icon: Cpu },
    { id: 'audit' as NavSection, label: 'Audit Trail', icon: History },
    { id: 'system' as NavSection, label: 'System Health', icon: ShieldCheck },
  ]

  return (
    <aside className="w-64 border-r border-[#334155] bg-[#1e293b] flex flex-col h-full shrink-0">
      {/* Brand logo */}
      <div className="h-16 px-6 flex items-center border-b border-[#334155] gap-3">
        <div className="h-8 w-8 rounded-lg bg-indigo-500 flex items-center justify-center text-white font-bold shadow-md shadow-indigo-500/20">
          H
        </div>
        <div>
          <span className="font-bold text-slate-100 text-lg tracking-tight">HunterOS</span>
          <span className="text-xs font-semibold text-indigo-400 block -mt-1 uppercase tracking-widest">Engage</span>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
        {menuItems.map((item) => {
          const Icon = item.icon
          const active = currentSection === item.id

          return (
            <button
              key={item.id}
              onClick={() => onSelectSection(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                active
                  ? 'bg-indigo-500 text-white shadow-md shadow-indigo-500/10'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              <Icon className="h-4.5 w-4.5" />
              {item.label}
            </button>
          )
        })}

        {process.env.ENABLE_DEVELOPER_TOOLS === 'true' && role === 'Founder' && (
          <>
            <hr className="border-[#334155] my-4" />
            <button
              onClick={() => onSelectSection('developer_tools')}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                currentSection === 'developer_tools'
                  ? 'bg-indigo-500 text-white shadow-md shadow-indigo-500/10'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              <Sliders className="h-4.5 w-4.5 text-amber-500" />
              Developer Tools
            </button>
          </>
        )}
      </nav>

      {/* Operator profile card */}
      <div className="p-4 border-t border-[#334155] bg-[#0f172a]/50">
        <div className="flex items-center gap-3 mb-4">
          <div className="h-9 w-9 rounded-full bg-slate-700 flex items-center justify-center text-slate-200 font-bold text-sm">
            {role ? role.substring(0, 2).toUpperCase() : 'OP'}
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-slate-200 truncate">
              {user?.full_name || 'Operator'}
            </p>
            <span className="inline-block text-[10px] font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded uppercase border border-indigo-500/10">
              {role || 'Viewer'}
            </span>
          </div>
        </div>

        <button
          onClick={logout}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-rose-400 bg-rose-500/5 hover:bg-rose-500/10 border border-rose-500/10 transition-all cursor-pointer"
        >
          <LogOut className="h-4 w-4" />
          Disconnect
        </button>
      </div>
    </aside>
  )
}

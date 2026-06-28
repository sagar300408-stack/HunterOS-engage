import React, { useState } from 'react'
import { ConversationCard } from './ConversationCard'
import { Search, SlidersHorizontal, ChevronLeft, ChevronRight } from 'lucide-react'
import type { ConversationSummary, ConversationPage } from '../../types'

interface ConversationFeedProps {
  pageData: ConversationPage | undefined
  loading: boolean
  selectedId: string | null
  onSelect: (id: string) => void
  page: number
  onPageChange: (p: number) => void
  search: string
  onSearchChange: (s: string) => void
  stageFilter: string
  onStageFilterChange: (s: string) => void
}

export const ConversationFeed: React.FC<ConversationFeedProps> = ({
  pageData,
  loading,
  selectedId,
  onSelect,
  page,
  onPageChange,
  search,
  onSearchChange,
  stageFilter,
  onStageFilterChange,
}) => {
  const [showFilters, setShowFilters] = useState(false)

  const stages = [
    { label: 'All Stages', value: '' },
    { label: 'Research', value: 'Research' },
    { label: 'Comparing Options', value: 'Comparing Options' },
    { label: 'Ready to Schedule', value: 'Ready to Schedule' },
    { label: 'Negotiation', value: 'Negotiation' },
    { label: 'Purchase Ready', value: 'Purchase Ready' },
  ]

  return (
    <div className="flex flex-col h-full border-r border-[#334155] bg-[#1e293b]/20">
      {/* Search Header */}
      <div className="p-4 border-b border-[#334155] space-y-3">
        <div className="relative">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
            <Search className="h-4 w-4" />
          </span>
          <input
            type="text"
            className="input pl-10"
            placeholder="Search active chats..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>

        <div className="flex justify-between items-center">
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
            Conversations ({pageData?.total ?? 0})
          </span>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-lg border transition-all cursor-pointer ${
              showFilters || stageFilter
                ? 'border-indigo-500/35 bg-indigo-500/5 text-indigo-400'
                : 'border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Filters
          </button>
        </div>

        {/* Additional Filters dropdown */}
        {showFilters && (
          <div className="p-3 bg-[#1e293b]/60 border border-slate-700 rounded-xl space-y-2 fade-in">
            <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Filter by buying stage
            </label>
            <select
              className="input text-xs"
              value={stageFilter}
              onChange={(e) => onStageFilterChange(e.target.value)}
            >
              {stages.map((st) => (
                <option key={st.value} value={st.value} className="bg-[#1e293b]">
                  {st.label}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* List Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 card skeleton"></div>
          ))
        ) : !pageData?.items || pageData.items.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No active conversations match criteria.
          </div>
        ) : (
          pageData.items.map((convo) => (
            <ConversationCard
              key={convo.id}
              summary={convo}
              active={selectedId === convo.id}
              onClick={() => onSelect(convo.id)}
            />
          ))
        )}
      </div>

      {/* Pagination Controls */}
      {pageData && pageData.total > pageData.page_size && (
        <div className="p-4 border-t border-[#334155] flex items-center justify-between bg-[#1e293b]/40">
          <span className="text-xs text-slate-400">
            Page {page} of {Math.ceil(pageData.total / pageData.page_size)}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page === 1}
              className="btn-ghost p-1.5 disabled:opacity-30 cursor-pointer"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={!pageData.has_next}
              className="btn-ghost p-1.5 disabled:opacity-30 cursor-pointer"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

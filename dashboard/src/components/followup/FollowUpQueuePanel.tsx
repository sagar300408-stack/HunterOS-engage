import React, { useState } from 'react'
import { fetchFollowUpQueue } from '../../api/followup'
import { useQuery } from '@tanstack/react-query'
import FollowUpCard from './FollowUpCard'
import FollowUpDetailModal from './FollowUpDetailModal'
import { RefreshCw, Search } from 'lucide-react'

export default function FollowUpQueuePanel() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('scheduled')
  
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['followup_queue', statusFilter],
    queryFn: () => fetchFollowUpQueue(statusFilter !== 'all' ? statusFilter : undefined, undefined, 1, 100),
    refetchInterval: 10000
  })

  return (
    <div className="flex flex-col h-full bg-[#1e293b]/20 border border-slate-700 rounded-xl overflow-hidden">
      <div className="p-4 border-b border-slate-700 bg-slate-800/30 flex justify-between items-center">
        <h3 className="font-bold text-slate-200 text-sm">Follow-up Queue</h3>
        <div className="flex items-center gap-3">
          <select 
            value={statusFilter} 
            onChange={e => setStatusFilter(e.target.value)}
            className="text-xs bg-[#0f172a] border border-slate-700 text-slate-300 rounded px-2 py-1 outline-none"
          >
            <option value="all">All Statuses</option>
            <option value="scheduled">Scheduled</option>
            <option value="executing">Executing</option>
            <option value="sent">Sent</option>
            <option value="replied">Replied</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <button onClick={() => refetch()} className="text-slate-400 hover:text-slate-200">
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-24 card skeleton"></div>)
        ) : data?.items.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 p-8 text-center space-y-3">
            <Search className="h-8 w-8 opacity-50" />
            <p className="text-sm">No follow-ups found in this queue.</p>
          </div>
        ) : (
          data?.items.map(item => (
            <FollowUpCard 
              key={item.id} 
              item={item} 
              onClick={() => setSelectedId(item.id)} 
            />
          ))
        )}
      </div>

      {selectedId && (
        <FollowUpDetailModal 
          id={selectedId} 
          onClose={() => setSelectedId(null)} 
          onRefresh={refetch} 
        />
      )}
    </div>
  )
}

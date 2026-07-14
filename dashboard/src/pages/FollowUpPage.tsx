import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchFollowUpOverview } from '../api/followup'
import FollowUpOverview from '../components/followup/FollowUpOverview'
import FollowUpQueuePanel from '../components/followup/FollowUpQueuePanel'
import FollowUpAnalytics from '../components/followup/FollowUpAnalytics'

export default function FollowUpPage() {
  const { data: overview, isLoading } = useQuery({
    queryKey: ['followup_overview'],
    queryFn: fetchFollowUpOverview,
    refetchInterval: 15000
  })

  return (
    <div className="space-y-6 h-full flex flex-col fade-in">
      {/* Top metrics row */}
      <div className="shrink-0">
        <FollowUpOverview stats={overview} loading={isLoading} />
      </div>
      
      {/* Main split view */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0">
        {/* Left: Interactive Queue */}
        <div className="lg:col-span-2 h-[calc(100vh-280px)] min-h-[400px]">
          <FollowUpQueuePanel />
        </div>
        
        {/* Right: Strategy Analytics */}
        <div className="lg:col-span-1 h-[calc(100vh-280px)] min-h-[400px]">
          <FollowUpAnalytics stats={overview} loading={isLoading} />
        </div>
      </div>
    </div>
  )
}

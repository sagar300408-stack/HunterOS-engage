import React, { useState } from 'react'
import {
  Users, Save, Edit3, ShieldAlert, Cpu, Heart, MapPin, Calendar, CircleDollarSign
} from 'lucide-react'
import { updateCustomer } from '../../api/dashboard'
import type { CustomerProfile as ProfileType } from '../../types'

interface CustomerProfileProps {
  profile: ProfileType | undefined
  loading: boolean
  onRefresh: () => void
}

export const CustomerProfile: React.FC<CustomerProfileProps> = ({ profile, loading, onRefresh }) => {
  const [activeTab, setActiveTab] = useState<'memory' | 'qual' | 'edit'>('memory')
  
  // Edit Form State
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [notes, setNotes] = useState('')
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)
  const [success, setSuccess] = useState(false)

  // Initialize edit form when tab changes
  const initForm = () => {
    if (profile) {
      setName(profile.name || '')
      setEmail(profile.email || '')
      setNotes(profile.notes || '')
      setStatus(profile.status || 'new')
      setSuccess(false)
    }
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!profile) return
    setSaving(true)
    setSuccess(false)
    try {
      await updateCustomer(profile.id, { name, email, notes, status })
      setSuccess(true)
      onRefresh()
    } catch (err) {
      console.error('Failed to update profile', err)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <div className="card h-full skeleton"></div>
  }

  if (!profile) {
    return (
      <div className="card h-full flex flex-col items-center justify-center text-slate-500 text-center p-8">
        <Users className="h-12 w-12 text-slate-700 mb-3" />
        <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest">Select Customer</h3>
        <p className="text-xs text-slate-500 mt-1">
          Select a customer profile to inspect memories, review AI qualifications, or manually update contact records.
        </p>
      </div>
    )
  }

  return (
    <div className="card h-full flex flex-col justify-between overflow-hidden">
      
      {/* Header Info */}
      <div className="space-y-4 shrink-0 pb-4 border-b border-slate-700/60">
        <div className="flex items-center gap-3">
          <div className="h-12 w-12 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center font-bold text-lg">
            {profile.name ? profile.name.charAt(0).toUpperCase() : 'U'}
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-200">{profile.name || 'Unnamed Profile'}</h2>
            <span className="inline-block text-[10px] font-bold uppercase px-2 py-0.5 mt-1 rounded bg-slate-800 text-slate-400 border border-slate-700">
              {profile.status}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-2 rounded bg-[#0f172a]/20 border border-slate-800">
            <span className="text-slate-500 block">Phone</span>
            <span className="font-semibold text-slate-300 font-mono">{profile.phone}</span>
          </div>
          <div className="p-2 rounded bg-[#0f172a]/20 border border-slate-800">
            <span className="text-slate-500 block">Email</span>
            <span className="font-semibold text-slate-300 truncate block">{profile.email || '—'}</span>
          </div>
        </div>

        {/* Tab Selection */}
        <div className="flex border-b border-slate-700/50 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('memory')}
            className={`flex-1 pb-2 border-b-2 text-center transition-all ${
              activeTab === 'memory'
                ? 'border-indigo-500 text-slate-200 font-bold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Memory System
          </button>
          <button
            onClick={() => setActiveTab('qual')}
            className={`flex-1 pb-2 border-b-2 text-center transition-all ${
              activeTab === 'qual'
                ? 'border-indigo-500 text-slate-200 font-bold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            AI Qualification
          </button>
          <button
            onClick={() => {
              setActiveTab('edit')
              initForm()
            }}
            className={`flex-1 pb-2 border-b-2 text-center transition-all ${
              activeTab === 'edit'
                ? 'border-indigo-500 text-slate-200 font-bold'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            Edit Profile
          </button>
        </div>
      </div>

      {/* Tab Panel Body */}
      <div className="flex-1 overflow-y-auto py-4 min-h-[300px]">
        {activeTab === 'memory' && (
          <div className="space-y-5 fade-in text-xs">
            {/* Memory Summary */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">AI Rolling Summary</span>
              <p className="p-3.5 rounded-lg bg-slate-800/40 border border-slate-700 text-slate-300 leading-relaxed font-sans">
                {profile.memory?.summary || 'No rolling memory created yet. Send a message to seed the memory engine.'}
              </p>
            </div>

            {/* Structured Fields */}
            <div className="space-y-3">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Extracted Customer Facts</span>
              <div className="space-y-2">
                
                {/* Budget */}
                <div className="p-3 rounded-lg bg-[#0f172a]/20 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CircleDollarSign className="h-4 w-4 text-indigo-400" />
                    <span className="text-slate-400">Budget Target:</span>
                  </div>
                  <span className="font-semibold text-slate-200 font-mono">
                    {profile.memory?.budget?.value || '—'}
                  </span>
                </div>

                {/* Timeline */}
                <div className="p-3 rounded-lg bg-[#0f172a]/20 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-indigo-400" />
                    <span className="text-slate-400">Timeline:</span>
                  </div>
                  <span className="font-semibold text-slate-200">
                    {profile.memory?.timeline?.value || '—'}
                  </span>
                </div>

                {/* Location */}
                <div className="p-3 rounded-lg bg-[#0f172a]/20 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-indigo-400" />
                    <span className="text-slate-400">Location Pref:</span>
                  </div>
                  <span className="font-semibold text-slate-200">
                    {profile.memory?.preferred_location?.value || '—'}
                  </span>
                </div>

                {/* Interests */}
                <div className="p-3 rounded-lg bg-[#0f172a]/20 border border-slate-800 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Heart className="h-4 w-4 text-indigo-400" />
                    <span className="text-slate-400">Interests:</span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {profile.memory?.interests && profile.memory.interests.length > 0 ? (
                      profile.memory.interests.map((it, idx) => (
                        <span key={idx} className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/10 rounded px-2 py-0.5">
                          {it}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-500 italic">—</span>
                    )}
                  </div>
                </div>

              </div>
            </div>
          </div>
        )}

        {activeTab === 'qual' && (
          <div className="space-y-5 fade-in text-xs">
            {/* Qualification Panel */}
            <div className="flex items-center justify-between p-4 rounded-xl border border-slate-700 bg-slate-800/30">
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Quality Grade</span>
                <span className="text-3xl font-extrabold text-indigo-400 font-mono mt-0.5 block">
                  {profile.qualification?.grade || 'F'}
                </span>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Extracted Score</span>
                <span className="text-xl font-bold text-slate-200 mt-0.5 block font-mono">
                  {profile.qualification?.score ?? 0} <span className="text-slate-500">/ 100</span>
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Qualification Signals</span>
              <div className="space-y-2">
                <div className="p-3 rounded-lg bg-[#0f172a]/20 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Status</span>
                  <span className={`badge ${profile.qualification?.qualified ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/10' : 'bg-rose-500/10 text-rose-400 border-rose-500/10'}`}>
                    {profile.qualification?.qualified ? 'Qualified Lead' : 'Unqualified Inquiry'}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-[#0f172a]/20 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Urgency Level</span>
                  <span className="font-semibold text-slate-300 uppercase font-mono">{profile.qualification?.urgency || 'unknown'}</span>
                </div>
                <div className="p-3 rounded-lg bg-[#0f172a]/20 border border-slate-800 flex items-center justify-between">
                  <span className="text-slate-400">Next Action Goal</span>
                  <span className="font-semibold text-indigo-400">{profile.qualification?.next_action || 'Continue Conversations'}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'edit' && (
          <form onSubmit={handleSave} className="space-y-4 fade-in text-xs">
            {success && (
              <div className="p-3 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-center font-semibold">
                Customer record updated successfully!
              </div>
            )}
            
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Full Name</label>
              <input
                type="text"
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Email Address</label>
              <input
                type="email"
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Lead Status</label>
              <select
                className="input bg-[#1e293b]"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="new">New (uncontacted)</option>
                <option value="active">Active conversation</option>
                <option value="blocked">Blocked / Ignored</option>
                <option value="completed">Completed transaction</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Operator Notes</label>
              <textarea
                rows={4}
                className="input font-sans py-2"
                placeholder="Manual operator follow-up summaries or override insights..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={saving}
              className="btn-primary w-full flex items-center justify-center gap-1.5 py-2.5 mt-2 cursor-pointer"
            >
              <Save className="h-4 w-4" />
              {saving ? 'Saving...' : 'Apply Details'}
            </button>
          </form>
        )}
      </div>

      {/* Footer Timestamp */}
      <div className="shrink-0 pt-4 border-t border-slate-700/60 text-[10px] text-slate-500">
        <span>Last message activity: {profile.last_interaction ? new Date(profile.last_interaction).toLocaleString() : '—'}</span>
      </div>
    </div>
  )
}

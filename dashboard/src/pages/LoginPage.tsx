import React, { useState } from 'react'
import { login, fetchMe } from '../api/dashboard'
import { useAuthStore } from '../store/authStore'
import { Lock, Mail, Server } from 'lucide-react'

export const LoginPage = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((s) => s.login)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const data = await login(email, password)
      // Save auth credentials
      setAuth(
        data.access_token,
        { id: '', email, role: data.role, workspace_id: data.workspace_id, created_at: '' },
        data.role,
        data.workspace_id
      )
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Authentication failed. Please verify credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0f172a] px-4">
      <div className="w-full max-w-md glass p-8 shadow-2xl relative overflow-hidden">
        {/* Glow Effects */}
        <div className="absolute -top-16 -left-16 w-32 h-32 bg-indigo-500/20 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-16 -right-16 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl"></div>

        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 mb-3 border border-indigo-500/20">
            <Server className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">HunterOS Engage</h1>
          <p className="text-sm text-slate-400 mt-1">AI-Powered Sales Mission Control</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {error && (
            <div className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-3 text-sm text-rose-400 text-center animate-pulse">
              {error}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Operator Email
            </label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                <Mail className="h-4 w-4" />
              </span>
              <input
                type="email"
                required
                className="input pl-10"
                placeholder="admin@hunteros.ai"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Password
              </label>
            </div>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-slate-500">
                <Lock className="h-4 w-4" />
              </span>
              <input
                type="password"
                required
                className="input pl-10"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full mt-2 py-3">
            {loading ? 'Securing Connection...' : 'Enter Mission Control'}
          </button>
        </form>

        <div className="mt-6 text-center text-xs text-slate-500">
          Demo: <span className="text-slate-400 font-mono">admin@hunteros.ai</span> / <span className="text-slate-400 font-mono">admin123</span>
        </div>
      </div>
    </div>
  )
}

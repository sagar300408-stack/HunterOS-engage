import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthState, User } from '../types'

interface AuthStore extends AuthState {
  login: (token: string, user: User, role: string, workspace_id: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      role: null,
      workspace_id: null,

      login: (token, user, role, workspace_id) =>
        set({ token, user, role, workspace_id }),

      logout: () =>
        set({ token: null, user: null, role: null, workspace_id: null }),
    }),
    { name: 'hunteros-auth' }
  )
)

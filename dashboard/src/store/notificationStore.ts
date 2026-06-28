import { create } from 'zustand'

export interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  timestamp: string
  read: boolean
}

interface NotificationStore {
  notifications: Notification[]
  unreadCount: number
  add: (n: Omit<Notification, 'id' | 'read' | 'timestamp'>) => void
  markAllRead: () => void
  dismiss: (id: string) => void
  clear: () => void
}

export const useNotificationStore = create<NotificationStore>((set, get) => ({
  notifications: [],
  unreadCount: 0,

  add: (n) => {
    const notification: Notification = {
      ...n,
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      read: false,
    }
    set((s) => ({
      notifications: [notification, ...s.notifications].slice(0, 50),
      unreadCount: s.unreadCount + 1,
    }))
  },

  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  dismiss: (id) =>
    set((s) => ({
      notifications: s.notifications.filter((n) => n.id !== id),
      unreadCount: s.notifications.filter((n) => n.id !== id && !n.read).length,
    })),

  clear: () => set({ notifications: [], unreadCount: 0 }),
}))

import React from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useAuthStore } from './store/authStore'
import { DashboardPage } from './pages/DashboardPage'
import { LoginPage } from './pages/LoginPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

export default function App() {
  const token = useAuthStore((s) => s.token)

  return (
    <QueryClientProvider client={queryClient}>
      {token ? <DashboardPage /> : <LoginPage />}
    </QueryClientProvider>
  )
}

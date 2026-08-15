import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import api from '../api/client'
import { fetchOverview, fetchCustomers } from '../api/dashboard'
import { useAuthStore } from '../store/authStore'
import { Sidebar } from '../components/layout/Sidebar'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import React from 'react'

// Spy on api methods to inspect requests without hitting the network
vi.spyOn(api, 'get')

describe('B2 Frontend Tenant Isolation', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({
      token: 'fake-token-workspace-a',
      user: { id: 'u1', full_name: 'Test', email: 'test@example.com', role: 'Operator', workspace_id: 'ws-a', created_at: '2023-01-01' },
      role: 'Operator',
      workspace_id: 'ws-a'
    })
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } }
    })
  })

  afterEach(() => {
    useAuthStore.getState().logout()
  })

  it('Test A: Authenticated API request attaches Authorization token', () => {
    // Inspect the Axios request interceptor directly
    // @ts-expect-error accessing internal axios properties for testing
    const requestInterceptor = api.interceptors.request.handlers[0]?.fulfilled
    expect(requestInterceptor).toBeDefined()
    
    const config = { headers: {} as Record<string, string> } as any
    const result = requestInterceptor(config) as any
    
    expect(result.headers.Authorization).toBe('Bearer fake-token-workspace-a')
  })

  it('Test B: No client-controlled tenant override in API calls', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: { success: true } })
    
    await fetchOverview()
    // It should request EXACTLY '/dashboard/overview' without any workspace query params injected by the client
    expect(api.get).toHaveBeenCalledWith('/dashboard/overview')
    
    vi.mocked(api.get).mockResolvedValueOnce({ data: { items: [], total: 0 } })
    await fetchCustomers({ search: 'Acme' })
    
    const callArgs = vi.mocked(api.get).mock.calls[1]
    const endpoint = callArgs[0]
    const config = callArgs[1]
    
    expect(endpoint).toBe('/dashboard/customers')
    // Ensure the params only contain business logic parameters, NOT workspace_id
    expect(config?.params?.search).toBe('Acme')
    expect(config?.params?.workspace_id).toBeUndefined()
    expect(config?.params?.workspace).toBeUndefined()
    expect(config?.params?.tenant_id).toBeUndefined()
  })

  it('Test C: Logout cache isolation clears QueryClient', async () => {
    // Pre-populate query client with User A's data
    queryClient.setQueryData(['overview'], { total_customers: 100 })
    expect(queryClient.getQueryData(['overview'])).toEqual({ total_customers: 100 })

    // Render the Sidebar where the disconnect button is
    render(
      <QueryClientProvider client={queryClient}>
        <Sidebar currentSection="overview" onSelectSection={() => {}} />
      </QueryClientProvider>
    )

    // Click Disconnect
    const disconnectBtn = screen.getByRole('button', { name: /disconnect/i })
    await userEvent.click(disconnectBtn)

    // 1. The Auth store MUST be cleared
    expect(useAuthStore.getState().token).toBeNull()
    expect(useAuthStore.getState().workspace_id).toBeNull()

    // 2. The React Query cache MUST be cleared to prevent cross-tenant data leaks
    expect(queryClient.getQueryData(['overview'])).toBeUndefined()
  })

  it('Test D: Foreign object handling (403/404)', async () => {
    // Mock a backend 403 Forbidden response (e.g., when trying to access Workspace B's customer)
    vi.mocked(api.get).mockRejectedValueOnce({
      response: { status: 403, data: { detail: 'Not authorized' } }
    })
    
    const ForeignDataComponent = () => {
      const { error, isError } = useQuery({
        queryKey: ['customerProfile', 'foreign-id'],
        queryFn: async () => {
          const res = await api.get('/dashboard/customers/foreign-id')
          return res.data
        }
      })
      
      if (isError) return <div data-testid="error-state">Access Denied</div>
      return <div data-testid="success-state">Profile Data</div>
    }

    render(
      <QueryClientProvider client={queryClient}>
        <ForeignDataComponent />
      </QueryClientProvider>
    )

    // The UI should show the safe error state
    await waitFor(() => {
      expect(screen.getByTestId('error-state')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('success-state')).toBeNull()

    // Ensure the cache DOES NOT contain the foreign object
    expect(queryClient.getQueryData(['customerProfile', 'foreign-id'])).toBeUndefined()
  })
})

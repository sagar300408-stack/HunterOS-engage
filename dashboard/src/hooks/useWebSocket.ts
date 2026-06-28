import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import { useNotificationStore } from '../store/notificationStore'

export const useWebSocket = () => {
  const queryClient = useQueryClient()
  const token = useAuthStore((s) => s.token)
  const addNotification = useNotificationStore((s) => s.add)
  const [connected, setConnected] = useState(false)
  const [clientsCount, setClientsCount] = useState(0)
  const socketRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!token) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/dashboard?token=${token}`

    const socket = new WebSocket(wsUrl)
    socketRef.current = socket

    socket.onopen = () => {
      setConnected(true)
      console.log('[WebSocket] Connected')
    }

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        const { event: eventName, data } = payload

        console.log(`[WebSocket] Event Received: ${eventName}`, data)

        // Handle standard real-time UI updates by invalidating React Query caches
        if (eventName === 'connected') {
          setClientsCount(data.clients || 0)
        } else if (eventName === 'conversation_updated') {
          queryClient.invalidateQueries({ queryKey: ['conversations'] })
          queryClient.invalidateQueries({ queryKey: ['conversationDetail', data.conversation_id] })
          queryClient.invalidateQueries({ queryKey: ['overview'] })
          
          addNotification({
            type: 'info',
            title: 'New Message',
            message: `New message in conversation: ${data.from_phone}`,
          })
        } else if (eventName === 'intent_extracted') {
          queryClient.invalidateQueries({ queryKey: ['conversationDetail', data.conversation_id] })
          queryClient.invalidateQueries({ queryKey: ['overview'] })
          
          if (data.confidence < 0.6) {
            addNotification({
              type: 'warning',
              title: 'Low Confidence Intent',
              message: `AI classified intent as "${data.intent}" with low confidence (${Math.round(data.confidence * 100)}%)`,
            })
          }
        } else if (eventName === 'customer_updated' || eventName === 'lead_stage_changed') {
          queryClient.invalidateQueries({ queryKey: ['customers'] })
          queryClient.invalidateQueries({ queryKey: ['customerProfile', data.customer_id] })
          queryClient.invalidateQueries({ queryKey: ['leads'] })
          queryClient.invalidateQueries({ queryKey: ['overview'] })
          
          addNotification({
            type: 'success',
            title: eventName === 'customer_updated' ? 'Customer Profile Updated' : 'Lead Stage Changed',
            message: `Customer ${data.customer_name || data.customer_id} updated successfully.`,
          })
        }
      } catch (err) {
        console.error('[WebSocket] Failed to parse message', err)
      }
    }

    socket.onclose = () => {
      setConnected(false)
      console.log('[WebSocket] Disconnected')
    }

    socket.onerror = (err) => {
      console.error('[WebSocket] Error', err)
    }

    // Ping interval to keep connection alive
    const interval = setInterval(() => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send('ping')
      }
    }, 30000)

    return () => {
      clearInterval(interval)
      socket.close()
    }
  }, [token, queryClient, addNotification])

  return { connected, clientsCount }
}

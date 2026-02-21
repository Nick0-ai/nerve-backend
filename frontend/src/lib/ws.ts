export interface WSEvent {
  type: 'az_price_update' | 'checkpoint_event' | 'migration_complete' | 'timeshift_scheduled' | 'connected' | 'pong'
  timestamp: string
  [key: string]: unknown
}

type Listener = (event: WSEvent) => void

let socket: WebSocket | null = null
let listeners: Listener[] = []
let reconnectTimer: ReturnType<typeof setTimeout> | null = null

function getWsUrl() {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/ws/feed`
}

export function connect() {
  if (socket?.readyState === WebSocket.OPEN) return

  socket = new WebSocket(getWsUrl())

  socket.onopen = () => {
    console.log('[NERVE WS] Connected')
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  socket.onmessage = (e) => {
    try {
      const event: WSEvent = JSON.parse(e.data)
      listeners.forEach((fn) => fn(event))
    } catch {
      // ignore parse errors
    }
  }

  socket.onclose = () => {
    console.log('[NERVE WS] Disconnected — reconnecting in 3s')
    reconnectTimer = setTimeout(connect, 3000)
  }

  socket.onerror = () => {
    socket?.close()
  }
}

export function subscribe(fn: Listener): () => void {
  listeners.push(fn)
  return () => {
    listeners = listeners.filter((l) => l !== fn)
  }
}

export function disconnect() {
  socket?.close()
  socket = null
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
}

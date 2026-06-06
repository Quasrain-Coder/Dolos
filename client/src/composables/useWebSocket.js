// client/src/composables/useWebSocket.js
import { ref } from 'vue'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'

export function useWebSocket() {
  const ws = ref(null)
  const roomStore = useRoomStore()
  const gameStore = useGameStore()
  let reconnectTimer = null

  function connect(roomId, playerId, token) {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = location.host
    const url = `${protocol}//${host}/ws/${roomId}?player_id=${playerId}&token=${token}`

    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      roomStore.connected = true
    }

    ws.value.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        roomStore.updateFromMessage(msg)
        gameStore.updateFromMessage(msg)

        if (msg.type === 'phase_change' && msg.phase !== 'waiting' && msg.phase !== 'game_over') {
          const currentPath = window.location.hash
          if (!currentPath.includes('/play')) {
            window.location.hash = `#/room/${roomId}/play`
          }
        }
      } catch (e) {
        console.error('WS message parse error:', e)
      }
    }

    ws.value.onclose = () => {
      roomStore.connected = false
      console.log('WebSocket disconnected, attempting reconnect...')
      reconnectTimer = setTimeout(() => {
        connect(roomId, playerId, token)
      }, 2000)
    }
  }

  function send(type, payload = {}) {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type, ...payload }))
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
  }

  return { connect, send, disconnect }
}

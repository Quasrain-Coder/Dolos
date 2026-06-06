// client/src/stores/room.js
import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const STORAGE_KEY = 'dolos_session'

function loadSession() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch { return {} }
}

function saveSession(roomId, myPlayerId, myToken) {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ roomId, myPlayerId, myToken }))
}

export const useRoomStore = defineStore('room', () => {
  // Restore session from sessionStorage (survives page refresh)
  const saved = loadSession()

  const roomId = ref(saved.roomId || '')
  const players = ref([])
  const myPlayerId = ref(saved.myPlayerId || '')
  const myToken = ref(saved.myToken || '')
  const phase = ref('waiting')
  const hostId = ref('')
  const connected = ref(false)

  // Persist credentials whenever they change
  watch([myPlayerId, myToken, roomId], () => {
    if (myPlayerId.value && myToken.value) {
      saveSession(roomId.value, myPlayerId.value, myToken.value)
    }
  }, { deep: true })

  const isHost = computed(() => myPlayerId.value === hostId.value)
  const playerCount = computed(() => players.value.length)
  const canStart = computed(() => isHost.value && playerCount.value >= 2 && phase.value === 'waiting')

  function setRoom(data) {
    roomId.value = data.id
    players.value = data.players
    hostId.value = data.host_id
    phase.value = data.phase
  }

  function updateFromMessage(msg) {
    if (msg.type === 'room_update') {
      players.value = msg.players
      hostId.value = msg.host_id
      if (msg.phase) phase.value = msg.phase
    }
    if (msg.type === 'phase_change') {
      phase.value = msg.phase
    }
  }

  return {
    roomId, players, myPlayerId, myToken, phase, hostId, connected,
    isHost, playerCount, canStart,
    setRoom, updateFromMessage,
  }
})

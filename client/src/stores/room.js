// client/src/stores/room.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useRoomStore = defineStore('room', () => {
  const roomId = ref('')
  const players = ref([])
  const myPlayerId = ref('')
  const myToken = ref('')
  const phase = ref('waiting')
  const hostId = ref('')
  const connected = ref(false)

  const isHost = computed(() => myPlayerId.value === hostId.value)
  const playerCount = computed(() => players.value.length)
  const canStart = computed(() => isHost.value && playerCount.value >= 4 && phase.value === 'waiting')

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

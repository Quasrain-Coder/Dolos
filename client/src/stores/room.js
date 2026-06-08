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
  const gameMode = ref('who_is_honest')

  // Auth state
  const currentUser = ref(null)
  const authChecked = ref(false)
  const authError = ref('')
  const showLoginModal = ref(false)

  const isLoggedIn = computed(() => currentUser.value !== null)

  // Persist credentials whenever they change
  watch([myPlayerId, myToken, roomId], () => {
    if (myPlayerId.value && myToken.value) {
      saveSession(roomId.value, myPlayerId.value, myToken.value)
    }
  }, { deep: true })

  const isHost = computed(() => myPlayerId.value === hostId.value)
  const playerCount = computed(() => players.value.length)
  const canStart = computed(() => isHost.value && playerCount.value >= 2 && phase.value === 'waiting')

  function initAuth() {
    const token = localStorage.getItem('dolos_user')
    if (!token) {
      authChecked.value = true
      return
    }
    fetch('/api/users/me', {
      headers: { 'Authorization': `Bearer ${token}` },
    })
      .then(resp => {
        if (!resp.ok) {
          localStorage.removeItem('dolos_user')
          return null
        }
        return resp.json()
      })
      .then(user => {
        if (user) {
          currentUser.value = user
        }
        authChecked.value = true
      })
      .catch(() => {
        authChecked.value = true
      })
  }

  async function login(username, password) {
    authError.value = ''
    const resp = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!resp.ok) {
      const data = await resp.json()
      authError.value = data.detail || '登录失败'
      return false
    }
    const data = await resp.json()
    localStorage.setItem('dolos_user', data.token)
    currentUser.value = data.user
    authError.value = ''
    return true
  }

  async function register(username, password) {
    authError.value = ''
    const resp = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!resp.ok) {
      const data = await resp.json()
      authError.value = data.detail || '注册失败'
      return false
    }
    const data = await resp.json()
    localStorage.setItem('dolos_user', data.token)
    currentUser.value = data.user
    authError.value = ''
    return true
  }

  async function logout() {
    const token = localStorage.getItem('dolos_user')
    if (token) {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
        })
      } catch {}
    }
    localStorage.removeItem('dolos_user')
    currentUser.value = null
  }

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
      if (msg.mode) gameMode.value = msg.mode
    }
    if (msg.type === 'phase_change') {
      phase.value = msg.phase
    }
  }

  return {
    roomId, players, myPlayerId, myToken, phase, hostId, connected, gameMode,
    isHost, playerCount, canStart,
    setRoom, updateFromMessage,
    // Auth
    currentUser, authChecked, authError, showLoginModal, isLoggedIn,
    initAuth, login, register, logout,
  }
})

<!-- client/src/views/JoinView.vue -->
<template>
  <div class="join-page">
    <div class="logo">
      <h1>🎭 DOLOS</h1>
      <p class="subtitle">瞎掰王 — 看谁会忽悠</p>
    </div>

    <div class="card">
      <div class="room-code-display">
        <span class="label">房间码</span>
        <span class="code">{{ roomCode }}</span>
      </div>

      <!-- Logged in: direct join -->
      <template v-if="roomStore.isLoggedIn && roomStore.currentUser">
        <div class="logged-in-name">{{ roomStore.currentUser.username }}</div>
        <button class="btn btn-primary btn-lg" @click="joinRoom" :disabled="joining">
          {{ joining ? '加入中...' : '🚪 加入房间' }}
        </button>
      </template>

      <!-- Not logged in: choose login or anonymous -->
      <template v-else>
        <button class="btn btn-secondary" @click="roomStore.showLoginModal = true">
          🔑 登录
        </button>

        <div class="divider">—— 或匿名加入 ——</div>

        <input
          v-model="nickname"
          class="input"
          placeholder="输入昵称..."
          maxlength="12"
          @keyup.enter="joinRoom"
        />
        <button class="btn btn-primary btn-lg" @click="joinRoom" :disabled="!nickname.trim() || joining">
          {{ joining ? '加入中...' : '🎭 匿名加入' }}
        </button>
      </template>

      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <LoginModal :visible="roomStore.showLoginModal" @close="onLoginClose" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRoomStore } from '../stores/room'
import LoginModal from './LoginModal.vue'

const route = useRoute()
const router = useRouter()
const roomStore = useRoomStore()

const roomCode = ref('')
const nickname = ref('')
const error = ref('')
const joining = ref(false)

onMounted(() => {
  roomStore.initAuth()
  roomCode.value = (route.params.roomCode || '').toUpperCase()
})

function onLoginClose() {
  roomStore.showLoginModal = false
  // After login, if logged in, auto-join
  if (roomStore.isLoggedIn) {
    joinRoom()
  }
}

async function joinRoom() {
  const name = roomStore.isLoggedIn && roomStore.currentUser
    ? roomStore.currentUser.username
    : nickname.value.trim()

  if (!name || !roomCode.value) return
  joining.value = true
  error.value = ''

  try {
    sessionStorage.removeItem('dolos_session')
    const body = { nickname: name }
    if (roomStore.currentUser) {
      body.user_id = roomStore.currentUser.id
    }
    const resp = await fetch(`/api/rooms/${roomCode.value}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!resp.ok) {
      const data = await resp.json()
      error.value = data.detail || '加入失败'
      joining.value = false
      return
    }
    const data = await resp.json()
    roomStore.roomId = data.room_id
    roomStore.myPlayerId = data.player_id
    roomStore.myToken = data.token
    roomStore.players = data.players
    router.push(`/room/${data.room_id}`)
  } catch (e) {
    error.value = '网络错误，请重试'
    joining.value = false
  }
}
</script>

<!-- client/src/views/HomeView.vue -->
<template>
  <div class="home">
    <div class="auth-bar">
      <template v-if="roomStore.isLoggedIn && roomStore.currentUser">
        <span class="auth-user" @click="showProfile = true">👤 {{ roomStore.currentUser.username }}</span>
        <button class="btn-auth" @click="showProfile = true">📊</button>
      </template>
      <button v-else class="btn-auth" @click="roomStore.showLoginModal = true">登录 / 注册</button>
    </div>

    <div class="logo">
      <h1>🎭 DOLOS</h1>
      <p class="subtitle">瞎掰王 — 看谁会忽悠</p>
    </div>

    <div class="card">
      <label class="label">你的昵称</label>
      <input
        v-model="nickname"
        class="input"
        placeholder="输入显示名称..."
        maxlength="12"
        @keyup.enter="createRoom"
      />

      <!-- Mode selector -->
      <div class="mode-selector">
        <label class="label">游戏模式</label>
        <div class="mode-options">
          <div
            class="mode-card"
            :class="{ active: selectedMode === 'classic' }"
            @click="selectedMode = 'classic'"
          >
            <span class="mode-icon">🎭</span>
            <span class="mode-name">经典模式</span>
            <span class="mode-desc">法官出题·编假答案·投票猜真</span>
          </div>
          <div
            class="mode-card"
            :class="{ active: selectedMode === 'who_is_honest' }"
            @click="selectedMode = 'who_is_honest'"
          >
            <span class="mode-icon">🕵️</span>
            <span class="mode-name">谁是老实人</span>
            <span class="mode-desc">隐藏角色·老实人说实话·大聪明来猜</span>
          </div>
        </div>
      </div>

      <div class="actions">
        <button class="btn btn-primary" @click="createRoom" :disabled="!nickname.trim()">
          ✨ 创建新房间
        </button>

        <div class="divider">—— 或 ——</div>

        <div class="join-row">
          <input
            v-model="roomCode"
            class="input"
            placeholder="房间码"
            maxlength="4"
            @keyup.enter="joinRoom"
          />
          <button class="btn btn-secondary" @click="joinRoom" :disabled="!nickname.trim() || !roomCode.trim()">
            加入
          </button>
        </div>
      </div>

      <p v-if="error" class="error">{{ error }}</p>
    </div>

    <LoginModal :visible="roomStore.showLoginModal" @close="roomStore.showLoginModal = false" />
    <ProfilePanel :visible="showProfile" @close="showProfile = false" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import LoginModal from './LoginModal.vue'
import ProfilePanel from './ProfilePanel.vue'

const router = useRouter()
const route = useRoute()
const roomStore = useRoomStore()

const nickname = ref('')
const roomCode = ref('')
const error = ref('')
const selectedMode = ref('classic')
const showProfile = ref(false)

// If URL has a room code (e.g. /#/join/KK4Z), pre-fill it
onMounted(async () => {
  roomStore.initAuth()
  const codeFromUrl = route.params.roomCode
  if (codeFromUrl) {
    roomCode.value = codeFromUrl.toUpperCase()
  }
  await new Promise(r => setTimeout(r, 200))
  if (roomStore.currentUser && !nickname.value) {
    nickname.value = roomStore.currentUser.username
  }
})

async function createRoom() {
  if (!nickname.value.trim()) return
  error.value = ''
  try {
    sessionStorage.removeItem('dolos_session')
    const body = {
      nickname: nickname.value.trim(),
      mode: selectedMode.value,
    }
    if (roomStore.currentUser) {
      body.user_id = roomStore.currentUser.id
    }
    const resp = await fetch('/api/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!resp.ok) {
      const data = await resp.json()
      error.value = data.detail || '创建失败'
      return
    }
    const data = await resp.json()
    roomStore.players = []
    roomStore.roomId = data.room_id
    roomStore.myPlayerId = data.player_id
    roomStore.myToken = data.token
    roomStore.hostId = data.host_id
    roomStore.gameMode = selectedMode.value
    router.push(`/room/${data.room_id}`)
  } catch (e) {
    error.value = '网络错误，请重试'
  }
}

async function joinRoom() {
  if (!nickname.value.trim() || !roomCode.value.trim()) return
  error.value = ''
  try {
    sessionStorage.removeItem('dolos_session')
    const body = {
      nickname: nickname.value.trim(),
    }
    if (roomStore.currentUser) {
      body.user_id = roomStore.currentUser.id
    }
    const resp = await fetch(`/api/rooms/${roomCode.value.trim().toUpperCase()}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!resp.ok) {
      const data = await resp.json()
      error.value = data.detail || '加入失败'
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
  }
}
</script>

<!-- client/src/views/HomeView.vue -->
<template>
  <div class="home">
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'

const router = useRouter()
const route = useRoute()
const roomStore = useRoomStore()

const nickname = ref('')
const roomCode = ref('')
const error = ref('')

// If URL has a room code (e.g. /#/join/KK4Z), pre-fill it
onMounted(() => {
  const codeFromUrl = route.params.roomCode
  if (codeFromUrl) {
    roomCode.value = codeFromUrl.toUpperCase()
  }
})

async function createRoom() {
  if (!nickname.value.trim()) return
  error.value = ''
  try {
    const resp = await fetch('/api/rooms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nickname: nickname.value.trim() }),
    })
    if (!resp.ok) {
      const data = await resp.json()
      error.value = data.detail || '创建失败'
      return
    }
    const data = await resp.json()
    roomStore.roomId = data.room_id
    roomStore.myPlayerId = data.player_id
    roomStore.myToken = data.token
    roomStore.hostId = data.host_id
    router.push(`/room/${data.room_id}`)
  } catch (e) {
    error.value = '网络错误，请重试'
  }
}

async function joinRoom() {
  if (!nickname.value.trim() || !roomCode.value.trim()) return
  error.value = ''
  try {
    const resp = await fetch(`/api/rooms/${roomCode.value.trim().toUpperCase()}/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nickname: nickname.value.trim() }),
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

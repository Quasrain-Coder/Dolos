<!-- client/src/views/RoomView.vue -->
<template>
  <div class="lobby">
    <div class="room-header">
      <h2>🚪 房间大厅</h2>
      <div class="room-code">
        <span class="label">房间码</span>
        <span class="code">{{ roomStore.roomId }}</span>
      </div>
    </div>

    <div class="card">
      <h3>玩家 ({{ roomStore.playerCount }})</h3>
      <div class="player-list">
        <div
          v-for="p in roomStore.players"
          :key="p.id"
          class="player-item"
          :class="{ me: p.id === roomStore.myPlayerId, host: p.is_host }"
        >
          <span class="player-icon">{{ p.is_host ? '👑' : '🎭' }}</span>
          <span class="player-name">{{ p.nickname }}</span>
          <span v-if="p.id === roomStore.myPlayerId" class="tag">你</span>
          <span v-if="p.is_host" class="tag host-tag">房主</span>
        </div>
      </div>

      <button
        v-if="roomStore.isHost"
        class="btn btn-primary btn-lg"
        :disabled="!roomStore.canStart"
        @click="startGame"
      >
        {{ roomStore.canStart ? '🎮 开始游戏' : `等待玩家加入 (至少4人，当前${roomStore.playerCount}人)` }}
      </button>
      <p v-else class="waiting-hint">等待房主开始游戏...</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import { useWebSocket } from '../composables/useWebSocket'

const route = useRoute()
const roomStore = useRoomStore()
const { connect, send } = useWebSocket()

onMounted(() => {
  const roomId = route.params.id
  connect(roomId, roomStore.myPlayerId, roomStore.myToken)
})

function startGame() {
  send('start_game')
}
</script>

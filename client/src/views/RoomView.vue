<!-- client/src/views/RoomView.vue -->
<template>
  <div class="lobby">
    <div class="room-header">
      <h2>🚪 房间大厅</h2>
      <div class="room-code">
        <span class="label">房间码</span>
        <span class="code">{{ roomStore.roomId }}</span>
        <button class="btn-copy" @click="copyInviteLink" :title="copied ? '已复制!' : '复制邀请链接'">
          {{ copied ? '✅' : '🔗' }}
        </button>
      </div>
      <div class="mode-badge">
        {{ roomStore.isClassic ? '🎭 经典模式' : '🕵️ 谁是老实人' }}
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
          <span class="player-name" :class="{ clickable: p.user_id }" @click.stop="toggleStats(p)">{{ p.nickname }}</span>
          <span v-if="p.id === roomStore.myPlayerId" class="tag">你</span>
          <span v-if="p.is_host" class="tag host-tag">房主</span>
          <PlayerStatsPopup
            v-if="selectedPid === p.id && p.user_id"
            :user-id="p.user_id"
            @close="selectedPid = null"
          />
        </div>
      </div>

      <div v-if="roomStore.isWhoIsHonest" class="mode-hint">
        <p>🕵️ <strong>谁是老实人</strong>：每回合随机分配隐藏角色 —— 老实人说真话，大聪明来猜，其他人编假话忽悠！</p>
      </div>

      <button
        v-if="roomStore.isHost"
        class="btn btn-primary btn-lg"
        :disabled="!roomStore.canStart"
        @click="startGame"
      >
        {{ roomStore.canStart ? '🎮 开始游戏' : `等待玩家加入 (至少2人，当前${roomStore.playerCount}人)` }}
      </button>
      <p v-else class="waiting-hint">等待房主开始游戏...</p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import { useWebSocket } from '../composables/useWebSocket'
import PlayerStatsPopup from '../components/PlayerStatsPopup.vue'

const route = useRoute()
const roomStore = useRoomStore()
const { connect, send } = useWebSocket()
const copied = ref(false)
const selectedPid = ref(null)

function toggleStats(p) {
  selectedPid.value = selectedPid.value === p.id ? null : p.id
}

onMounted(() => {
  roomStore.initAuth()
  const roomId = route.params.id
  connect(roomId, roomStore.myPlayerId, roomStore.myToken)
})

function copyInviteLink() {
  const url = `${window.location.origin}/#/join/${roomStore.roomId}`
  navigator.clipboard.writeText(url)
  copied.value = true
  setTimeout(() => copied.value = false, 2000)
}

function startGame() {
  send('start_game', { mode: roomStore.gameMode })
}
</script>

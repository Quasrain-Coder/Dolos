<template>
  <div class="round-table">
    <div
      v-for="p in roomStore.players"
      :key="p.id"
      class="table-seat"
      :class="{
        offline: !p.is_connected,
        submitted: gameStore.submittedPlayers.includes(p.id),
        voted: gameStore.votedPlayers.includes(p.id),
      }"
    >
      <div class="seat-avatar clickable" @click.stop="toggleStats(p)">
        <span class="seat-icon">{{ seatIcon(p) }}</span>
        <span v-if="gameStore.votedPlayers.includes(p.id)" class="seat-badge vote">🗳️</span>
        <span v-else-if="gameStore.submittedPlayers.includes(p.id)" class="seat-badge done">✅</span>
      </div>
      <span class="seat-name" :class="{ clickable: p.user_id }" @click.stop="toggleStats(p)">{{ p.nickname }}</span>
      <span class="seat-score">{{ p.score }}分</span>
      <PlayerStatsPopup
        v-if="selectedPid === p.id && p.user_id"
        :user-id="p.user_id"
        @close="selectedPid = null"
      />
      <div v-if="selectedPid === p.id && !p.user_id" class="stats-popup">
        <div class="stats-username">{{ p.nickname }}</div>
        <div style="color: var(--text-dim); font-size:13px; text-align:center;">未注册玩家，无历史战绩</div>
        <button class="stats-close" @click="selectedPid = null">✕</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import PlayerStatsPopup from './PlayerStatsPopup.vue'

const roomStore = useRoomStore()
const gameStore = useGameStore()
const selectedPid = ref(null)

function seatIcon(p) {
  if (!p.is_connected) return '💤'
  return '🎭'
}

function toggleStats(p) {
  selectedPid.value = selectedPid.value === p.id ? null : p.id
}
</script>

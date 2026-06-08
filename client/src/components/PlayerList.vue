<template>
  <div class="round-table">
    <div
      v-for="p in roomStore.players"
      :key="p.id"
      class="table-seat"
      :class="{
        judge: roomStore.isClassic && p.id === gameStore.judgeId,
        offline: !p.is_connected,
        submitted: gameStore.submittedPlayers.includes(p.id),
        voted: gameStore.votedPlayers.includes(p.id),
      }"
    >
      <div class="seat-avatar" :class="{ clickable: p.user_id }" @click.stop="p.user_id && toggleStats(p)">
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
  if (roomStore.isClassic && p.id === gameStore.judgeId) return '👨‍⚖️'
  return '🎭'
}

function toggleStats(p) {
  selectedPid.value = selectedPid.value === p.id ? null : p.id
}
</script>

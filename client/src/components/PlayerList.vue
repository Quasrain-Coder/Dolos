<template>
  <div class="player-list-bar">
    <div v-for="p in roomStore.players" :key="p.id" class="player-dot" :class="{ judge: p.id === gameStore.judgeId, offline: !p.is_connected }">
      <span class="dot-icon">{{ p.id === gameStore.judgeId ? '👨‍⚖️' : '🎭' }}</span>
      <span class="dot-name" :class="{ clickable: p.user_id }" @click.stop="toggleStats(p)">{{ p.nickname }}</span>
      <span class="dot-score">{{ p.score }}</span>
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

function toggleStats(p) {
  selectedPid.value = selectedPid.value === p.id ? null : p.id
}
</script>

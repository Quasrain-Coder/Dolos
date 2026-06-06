<template>
  <div class="player-list-bar">
    <div v-for="p in roomStore.players" :key="p.id" class="player-dot" :class="{ judge: p.id === gameStore.judgeId, offline: !p.is_connected }">
      <span class="dot-icon">{{ p.id === gameStore.judgeId ? '👨‍⚖️' : '🎭' }}</span>
      <span class="dot-name">{{ p.nickname }}</span>
      <span class="dot-score">{{ p.score }}</span>
    </div>
  </div>
</template>

<script setup>
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'

const roomStore = useRoomStore()
const gameStore = useGameStore()
</script>

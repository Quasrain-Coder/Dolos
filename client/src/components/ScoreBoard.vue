<template>
  <div class="scoreboard" v-if="gameStore.standings.length">
    <div class="scoreboard-header" @click="expanded = !expanded">
      <span>🏅 排行榜</span>
      <span>{{ expanded ? '▲' : '▼' }}</span>
    </div>
    <div v-if="expanded" class="scoreboard-body">
      <div v-for="(p, i) in gameStore.standings" :key="p.player_id" class="standing-row" :class="{ me: p.player_id === roomStore.myPlayerId }">
        <span class="rank">{{ medals[i] || i + 1 }}</span>
        <span class="name">{{ p.nickname }}</span>
        <span class="score">{{ p.score }}分</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useGameStore } from '../stores/game'
import { useRoomStore } from '../stores/room'

const gameStore = useGameStore()
const roomStore = useRoomStore()
const expanded = ref(true)
const medals = ['🥇', '🥈', '🥉']
</script>

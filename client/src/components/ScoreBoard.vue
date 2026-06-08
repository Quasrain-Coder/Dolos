<template>
  <div class="scoreboard" v-if="gameStore.standings.length">
    <div class="scoreboard-header" @click="expanded = !expanded">
      <span>🏅 排行榜</span>
      <span>{{ expanded ? '▲' : '▼' }}</span>
    </div>
    <div v-if="expanded" class="scoreboard-body">
      <div v-for="(p, i) in gameStore.standings" :key="p.player_id" class="standing-row" :class="{ me: p.player_id === roomStore.myPlayerId }">
        <span class="rank">{{ medals[i] || i + 1 }}</span>
        <span class="name" :class="{ clickable: playerUserId(p.player_id) }" @click.stop="toggleStats(p.player_id)">{{ p.nickname }}</span>
        <span class="score">{{ p.score }}分</span>
        <PlayerStatsPopup
          v-if="selectedPid === p.player_id && playerUserId(p.player_id)"
          :user-id="playerUserId(p.player_id)"
          @close="selectedPid = null"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useGameStore } from '../stores/game'
import { useRoomStore } from '../stores/room'
import PlayerStatsPopup from './PlayerStatsPopup.vue'

const gameStore = useGameStore()
const roomStore = useRoomStore()
const expanded = ref(true)
const medals = ['🥇', '🥈', '🥉']
const selectedPid = ref(null)

function playerUserId(pid) {
  const player = roomStore.players.find(p => p.id === pid)
  return player?.user_id || null
}

function toggleStats(pid) {
  selectedPid.value = selectedPid.value === pid ? null : pid
}
</script>

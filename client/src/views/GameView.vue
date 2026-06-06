<template>
  <div class="game">
    <ScoreBoard />

    <div class="game-main">
      <div v-if="roomStore.phase === 'drawing'" class="phase-waiting">
        <p v-if="gameStore.isJudge">你是法官，请抽题</p>
        <p v-else>等待法官 {{ judgeNickname }} 抽题...</p>
      </div>

      <AnswerInput v-if="roomStore.phase === 'answering' && !gameStore.isJudge" />
      <JudgePanel v-if="gameStore.isJudge && (roomStore.phase === 'drawing' || roomStore.phase === 'answering' || roomStore.phase === 'voting')" />
      <VotingPanel v-if="roomStore.phase === 'voting' && !gameStore.isJudge" />
      <RevealPanel v-if="roomStore.phase === 'revealing' || roomStore.phase === 'round_end'" />

      <div v-if="roomStore.phase === 'game_over'" class="game-over">
        <h2>🏆 游戏结束!</h2>
        <div class="final-standings">
          <div v-for="(p, i) in gameStore.standings" :key="p.player_id" class="final-row">
            <span class="rank">{{ ['🥇','🥈','🥉'][i] || `#${i+1}` }}</span>
            <span class="name">{{ p.nickname }}</span>
            <span class="score">{{ p.score }}分</span>
          </div>
        </div>
        <button class="btn btn-primary btn-lg" @click="$router.push('/')">返回首页</button>
      </div>
    </div>

    <!-- Host controls during reveal (visible regardless of being judge) -->
    <div v-if="roomStore.isHost && (roomStore.phase === 'revealing' || roomStore.phase === 'round_end')" class="host-controls">
      <button class="btn btn-primary btn-lg" @click="send('next_round')">▶ 下一回合</button>
      <button class="btn btn-secondary" @click="send('end_game')">🏁 结束游戏</button>
    </div>

    <JudgePanel v-if="gameStore.isJudge && roomStore.phase === 'revealing'" />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'
import ScoreBoard from '../components/ScoreBoard.vue'
import AnswerInput from '../components/AnswerInput.vue'
import VotingPanel from '../components/VotingPanel.vue'
import RevealPanel from '../components/RevealPanel.vue'
import JudgePanel from '../components/JudgePanel.vue'

const route = useRoute()
const roomStore = useRoomStore()
const gameStore = useGameStore()
const { connect, send } = useWebSocket()

const judgeNickname = computed(() => {
  const p = roomStore.players.find(p => p.id === gameStore.judgeId)
  return p ? p.nickname : '?'
})

onMounted(() => {
  if (!roomStore.connected) {
    connect(route.params.id, roomStore.myPlayerId, roomStore.myToken)
  }
})
</script>

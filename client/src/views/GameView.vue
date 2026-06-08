<template>
  <div class="game">
    <!-- Role badge for mode 2 -->
    <div v-if="roomStore.isWhoIsHonest && gameStore.myRole" class="role-badge-top" :class="gameStore.myRole">
      {{ gameStore.roleLabel }}
    </div>

    <ScoreBoard />

    <div class="game-main">
      <!-- DRAWING: waiting for judge (classic) or system (mode 2) -->
      <div v-if="roomStore.phase === 'drawing'" class="phase-waiting">
        <p v-if="roomStore.isClassic">
          {{ gameStore.isJudge ? '你是法官，请抽题' : `等待法官 ${judgeNickname} 抽题...` }}
        </p>
        <p v-else>系统准备中...</p>
      </div>

      <!-- ANSWERING -->
      <!-- Mode 1: non-judge players submit -->
      <AnswerInput v-if="roomStore.phase === 'answering' && roomStore.isClassic && !gameStore.isJudge" />
      <!-- Mode 2: honest + bluffers submit; detective watches -->
      <AnswerInput v-if="roomStore.phase === 'answering' && roomStore.isWhoIsHonest && !gameStore.isDetective" />
      <!-- Mode 2: detective sees question but doesn't submit -->
      <div v-if="roomStore.phase === 'answering' && roomStore.isWhoIsHonest && gameStore.isDetective" class="phase-waiting">
        <div class="question-card">
          <div class="label">这道题是</div>
          <div class="term">{{ gameStore.questionTerm }}</div>
          <div class="hint">🕵️ 等待其他玩家提交答案，之后由你来投票和猜测老实人</div>
        </div>
      </div>

      <!-- Judge panel (classic mode only) -->
      <JudgePanel v-if="roomStore.isClassic && gameStore.isJudge && (roomStore.phase === 'drawing' || roomStore.phase === 'answering' || roomStore.phase === 'voting')" />

      <!-- VOTING -->
      <!-- Mode 1: non-judge vote -->
      <VotingPanel v-if="roomStore.phase === 'voting' && roomStore.isClassic && !gameStore.isJudge" />
      <!-- Mode 2: all vote -->
      <VotingPanel v-if="roomStore.phase === 'voting' && roomStore.isWhoIsHonest" />

      <!-- REVEALING -->
      <RevealPanel v-if="roomStore.phase === 'revealing' || roomStore.phase === 'round_end'" />


      <!-- GAME OVER -->
      <div v-if="roomStore.phase === 'game_over'" class="game-over">
        <h2>🏆 游戏结束!</h2>
        <div class="final-standings">
          <div v-for="(p, i) in gameStore.standings" :key="p.player_id" class="final-row">
            <span class="rank">{{ ['🥇','🥈','🥉'][i] || `#${i+1}` }}</span>
            <span class="name" :class="{ clickable: playerUserId(p.player_id) }" @click.stop="toggleStats(p.player_id)">{{ p.nickname }}</span>
            <span class="score">{{ p.score }}分</span>
            <PlayerStatsPopup
              v-if="selectedPid === p.player_id && playerUserId(p.player_id)"
              :user-id="playerUserId(p.player_id)"
              @close="selectedPid = null"
            />
          </div>
        </div>
        <button class="btn btn-primary btn-lg" @click="$router.push('/')">返回首页</button>
      </div>
    </div>

    <!-- Round controls during reveal: all players click ready, host can end game -->
    <div
      v-if="(roomStore.phase === 'revealing' || roomStore.phase === 'round_end') && !(roomStore.isWhoIsHonest && gameStore.awaitingDetective)"
      class="host-controls"
    >
      <!-- Ready button for all players -->
      <button
        v-if="!gameStore.iAmReady"
        class="btn btn-primary btn-lg"
        @click="clickReady"
      >
        ✅ 就绪（{{ gameStore.readyCount }}/{{ gameStore.totalForReady }}）
      </button>
      <div v-else class="ready-done">
        ✅ 已就绪（等待其他人... {{ gameStore.readyCount }}/{{ gameStore.totalForReady }}）
      </div>

      <!-- Ready player list -->
      <div v-if="gameStore.readyPlayerIds.length > 0" class="ready-players">
        <span
          v-for="pid in gameStore.readyPlayerIds"
          :key="pid"
          class="ready-player-tag"
        >✅ {{ getPlayerName(pid) }}</span>
      </div>

      <!-- End game (host only) -->
      <button v-if="roomStore.isHost" class="btn btn-secondary" @click="send('end_game')">
        🏁 结束游戏
      </button>
    </div>

    <!-- Classic mode: judge panel during reveal -->
    <JudgePanel v-if="roomStore.isClassic && gameStore.isJudge && roomStore.phase === 'revealing'" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'
import ScoreBoard from '../components/ScoreBoard.vue'
import AnswerInput from '../components/AnswerInput.vue'
import VotingPanel from '../components/VotingPanel.vue'
import RevealPanel from '../components/RevealPanel.vue'
import JudgePanel from '../components/JudgePanel.vue'
import PlayerStatsPopup from '../components/PlayerStatsPopup.vue'

const route = useRoute()
const roomStore = useRoomStore()
const gameStore = useGameStore()
const { connect, send } = useWebSocket()

const judgeNickname = computed(() => {
  const p = roomStore.players.find(p => p.id === gameStore.judgeId)
  return p ? p.nickname : '?'
})

const selectedPid = ref(null)

function getPlayerName(pid) {
  const p = roomStore.players.find(p => p.id === pid)
  return p ? p.nickname : '?'
}

function playerUserId(pid) {
  const p = roomStore.players.find(p => p.id === pid)
  return p?.user_id || null
}

function toggleStats(pid) {
  selectedPid.value = selectedPid.value === pid ? null : pid
}

function clickReady() {
  gameStore.iAmReady = true
  send('ready_next_round')
}

onMounted(() => {
  if (!roomStore.connected) {
    connect(route.params.id, roomStore.myPlayerId, roomStore.myToken)
  }
})
</script>

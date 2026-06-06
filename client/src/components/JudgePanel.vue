<template>
  <div class="judge-panel">
    <div class="judge-badge">👨‍⚖️ 你是法官</div>

    <!-- DRAWING: draw a question -->
    <div v-if="roomStore.phase === 'drawing'">
      <button class="btn btn-primary btn-lg" @click="judgeAction('draw')">🃏 抽题</button>
    </div>

    <!-- ANSWERING: wait for players to submit -->
    <div v-if="roomStore.phase === 'answering'">
      <div class="judge-question-info card">
        <div class="label">题目</div>
        <div class="term">{{ gameStore.questionTerm }}</div>
        <div class="definition">{{ gameStore.judgeDefinition }}</div>
      </div>
      <p class="judge-hint">等待玩家提交答案...</p>
    </div>

    <!-- VOTING: wait for players to vote -->
    <div v-if="roomStore.phase === 'voting'">
      <p class="judge-hint">玩家正在投票...</p>
    </div>
  </div>
</template>

<script setup>
import { useRoomStore } from '../stores/room'
import { useGameStore } from '../stores/game'
import { useWebSocket } from '../composables/useWebSocket'

const roomStore = useRoomStore()
const gameStore = useGameStore()
const { send } = useWebSocket()

function judgeAction(action) {
  send('judge_action', { action })
}
</script>

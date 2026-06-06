<template>
  <div class="judge-panel">
    <div class="judge-badge">👨‍⚖️ 你是法官</div>

    <div v-if="roomStore.phase === 'drawing'">
      <button class="btn btn-primary btn-lg" @click="judgeAction('draw')">🃏 抽题</button>
    </div>

    <div v-if="roomStore.phase === 'answering'">
      <div class="judge-question-info card">
        <div class="label">题目</div>
        <div class="term">{{ gameStore.questionTerm }}</div>
        <div class="definition">{{ gameStore.judgeDefinition }}</div>
      </div>
      <button class="btn btn-warn btn-lg" @click="judgeAction('collect')">📥 收答案 → 进入投票</button>
    </div>

    <div v-if="roomStore.phase === 'voting'">
      <p class="judge-hint">玩家正在投票...</p>
      <button class="btn btn-warn btn-lg" @click="judgeAction('end_vote')">🔔 结束投票 → 揭晓</button>
    </div>

    <div v-if="roomStore.phase === 'revealing' || roomStore.phase === 'round_end'">
      <button v-if="roomStore.isHost" class="btn btn-primary btn-lg" @click="send('next_round')">▶ 下一回合</button>
      <button v-if="roomStore.isHost" class="btn btn-secondary" @click="send('end_game')">🏁 结束游戏</button>
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
